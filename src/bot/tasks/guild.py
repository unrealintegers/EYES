import heapq
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Optional

import aiocron
import aiohttp
from pytz import utc

from ..bot import EYESBot, BotTask
from ..models import WynncraftAPI
from ..utils.wynn import GuildMember


# TODO: GuildListUpdater should also trigger an update for GuildUpdater
class GuildListUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.update = aiocron.crontab("0 */3 * * *", func=self._update, start=False, tz=utc)

    async def init(self):
        # Do one update at the start
        self.update.call_func()
        self.update.start()

    async def _update(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(WynncraftAPI.GUILD_LIST) as response:
                if not response.ok:
                    self.bot.logger.error("Failed to fetch Guild List from Wynn API!")
                    return

                response = await response.json()

        info_existing = await self.bot.db.fetch_tup("SELECT name FROM guild_info")
        info_existing = list(*zip(*info_existing))
        update_existing = await self.bot.db.fetch_tup("SELECT name FROM guild_update_info")
        update_existing = list(*zip(*update_existing))

        guilds = response['guilds']

        new_guilds = [(g,) for g in guilds if g not in info_existing]
        guild_update = {(g, dt.utcnow(), 0, td(days=1)) for g in guilds if g not in update_existing}
        await self.bot.db.copy_to("COPY guild_info (name) FROM STDIN", new_guilds)
        await self.bot.db.copy_to("COPY guild_update_info FROM STDIN", guild_update)

        # remove old guilds
        deleted_guilds = {(g,) for g in info_existing if g not in guilds}
        await self.bot.db.run_batch("""
            WITH deleted_guild AS (
                DELETE FROM guild_info 
                WHERE name = %s
                RETURNING * 
            ) INSERT INTO deleted_guild_info (name, prefix, level, size, deleted) 
            SELECT deleted_guild.*, NOW() FROM deleted_guild
        """, deleted_guilds)
        # TODO: Member history


class GuildUpdater(BotTask):
    """A priority-queue-based implementation to update guild details
       with exponential backoff strategy and rate limit handling"""

    def __init__(self, bot):
        super().__init__(bot)

        self.pq = []

        self.next = aiocron.crontab('* * * * * */3', func=self._next, start=False)

    async def init(self):
        await self.build_pq()

        self.next.start()

    async def _next(self):
        if self.pq:  # is not empty
            # We check that it is in fact time to update the smallest item
            if dt.now().timestamp() > self.pq[0][0]:
                # Gets the first element and updates it
                _, guild_name = heapq.heappop(self.pq)
                if next_update := await self.update_guild(guild_name):
                    # Re-adds it back to the queue with the scheduled next update
                    heapq.heappush(self.pq, (next_update, guild_name))

    async def build_pq(self):
        guilds = await self.bot.db.fetch_dict("SELECT name, next_update FROM guild_update_info")
        for guild in guilds:
            guild_name = guild.get('name')
            timestamp = guild.get('next_update', dt.now()).timestamp()
            heapq.heappush(self.pq, (timestamp, guild_name))

    @staticmethod
    def calc_next_interval(interval, no_diff_days, num_changes) -> td:
        MIN_INTERVAL = td(hours=6)
        MAX_INTERVAL = td(days=8)

        # If diff = 0 for more than 5 days, increase interval
        if num_changes == 0:
            if interval < td(days=1) and no_diff_days >= 2:
                interval = td(days=1)
            elif no_diff_days >= 4:
                interval *= 2
        elif num_changes != 0:
            if interval > td(days=1):
                interval = td(days=1)
            elif num_changes > 1:
                interval /= 2

        interval = max(min(interval, MAX_INTERVAL), MIN_INTERVAL)
        return interval

    async def update_guild(self, guild_name) -> Optional[float]:
        """Fetches 1 guild from the API and updates it."""

        url = WynncraftAPI.GUILD_STATS.format(guild_name=guild_name)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if not response.ok:
                    self.bot.logger.error(f"Failed to fetch Stats of {guild_name} from Wynncraft API.")
                    return
                else:
                    response = await response.json()

        # We grab the prefix and additionally add it to a prefix path for faster lookups
        prefix = response['prefix']

        # Now we get the members and return a number for change between this and last iteration
        member_info = list(map(lambda m: GuildMember.from_data(m).to_dict(), response['members']))
        print(guild_name)
        old_member_info = await self.bot.db.fetch_dict("SELECT name, uuid, rank, joined, contributed FROM guild_player "
                                                       "WHERE guild = %s", (guild_name,))

        members = {member['uuid']: member for member in member_info}
        old_members = {member['uuid']: member for member in old_member_info}
        num_changes = len(members.keys() | old_members.keys()) - len(members.keys() & old_members.keys())

        guild_player_insert = {(guild_name, uuid, member['name'], member['rank'],
                                member['joined'], member['contributed'])
                               for uuid, member in members.items() if uuid not in old_members.keys()}
        await self.bot.db.copy_to("COPY guild_player FROM STDIN", guild_player_insert)

        # Member history tracking
        await self.process_member_changes(old_members, members)

        # Calculate XP transitions
        await self.update_xp(guild_name, old_members, members)

        # Record this update
        update_info = await self.bot.db.fetch_tup("SELECT update_interval, no_diff_days FROM guild_update_info "
                                                  "WHERE name = %s", (guild_name,))

        if len(update_info) != 1:
            raise ValueError(f"Guild not found or multiple guilds found of name {guild_name} in guild_update_info")
        update_info = update_info[0]

        interval = update_info[0] or td(days=1)
        no_diff_days = update_info[1] or 0

        if num_changes == 0:
            no_diff_days += interval.total_seconds() / (60 * 60 * 24)
        else:
            no_diff_days = 0

        next_interval = self.calc_next_interval(interval, no_diff_days, num_changes)
        next_update = dt.now() + next_interval

        await self.bot.db.run("UPDATE guild_update_info "
                              "SET next_update = %s, no_diff_days = %s, update_interval = %s "
                              "WHERE name = %s",
                              (next_update, no_diff_days, next_interval, guild_name))
        await self.bot.db.run("UPDATE guild_info "
                              "SET prefix = %s, level = %s, size = %s "
                              "WHERE name = %s",
                              (prefix, response.get('level'), len(members), guild_name))

        return next_update.timestamp()

    async def process_member_changes(self, old_members, new_members):
        pass

    async def update_xp(self, guild_name, old_members, new_members):
        now = dt.now()
        total = 0
        update_list = []
        for member_uuid in new_members:
            old_xp = old_members.get(member_uuid, {}).get('contributed') or 0
            new_xp = new_members[member_uuid].get('contributed') or old_xp
            gained = new_xp - old_xp
            update_list.append((guild_name, member_uuid, now, gained))
            total += gained

        # TODO: implement start/end times
        await self.bot.db.copy_to("COPY player_xp FROM STDIN", update_list)
        await self.bot.db.run("INSERT INTO guild_xp VALUES (%s, %s, %s)", (guild_name, now, total))

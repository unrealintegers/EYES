import asyncio
import heapq
from datetime import datetime as dt
from datetime import timedelta as td
from typing import Optional

import aiocron
import aiohttp
import requests
from pytz import utc

from ..bot import EYESBot, BotTask
from ..utils.wynn import GuildMember


# TODO: GuildListUpdater should also trigger an update for GuildUpdater
class GuildListUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        # Do one update at the start
        self.update().call_func()
        self.update().start()

    def path(self):
        return self.bot.db.child('wynncraft').child('guilds')

    def update(self):
        @aiocron.crontab("0 */3 * * *", start=False, tz=utc)
        async def wrapper():
            response = requests.get("https://api.wynncraft.com/public_api.php?action=guildList")

            if not response.ok:
                self.bot.logger.error("Failed to fetch from Wynn API!")
                return
            else:
                response = response.json()

            try:
                existing_guilds = set(map(lambda x: x.key(), self.path().get().each()))
            except TypeError:
                existing_guilds = set()

            guilds = response['guilds']
            one_day = td(days=1).total_seconds()
            guilddict = {g: {'name': g, 'interval': one_day, 'no_diff_days': 0, 'next_update': 0}
                         for g in guilds if g not in existing_guilds}

            self.path().update(guilddict)

        return wrapper


class GuildUpdater(BotTask):
    """A priority-queue-based implementation to update guild details
       with exponential backoff strategy and rate limit handling"""

    def __init__(self, bot):
        super().__init__(bot)

        self.pq = []
        self.build_pq()

        asyncio.create_task(self.next())

    def guild_path(self):
        return self.bot.db.child('wynncraft').child('guilds')

    def deleted_path(self):
        return self.bot.db.child('wynncraft').child('deleted_guilds')

    def prefix_path(self):
        return self.bot.db.child('wynncraft').child('prefixes')

    async def next(self):
        if self.pq:  # is not empty
            # We check that it is in fact time to update the smallest item
            if dt.now().timestamp() > self.pq[0][0]:
                # Gets the first element and updates it
                _, guild_name = heapq.heappop(self.pq)
                if next_update := await self.update_guild(guild_name):
                    # Re-adds it back to the queue with the scheduled next update
                    heapq.heappush(self.pq, (next_update, guild_name))

        # 1 request per 5s
        await asyncio.sleep(5)
        asyncio.create_task(self.next())

    def build_pq(self):
        guilds = self.guild_path().get().each()
        for guild in guilds:
            guild_name = guild.key()
            timestamp = guild.val()['next_update']
            heapq.heappush(self.pq, (timestamp, guild_name))

    @staticmethod
    def calc_next_interval(interval, no_diff_days, num_changes) -> td:
        MIN_INTERVAL = td(hours=6)
        MAX_INTERVAL = td(days=8)

        # If diff = 0 for more than 5 days, increase interval
        if num_changes == 0:
            if interval < td(days=1) and no_diff_days >= 4:
                interval = td(days=1)
            else:
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
        self.bot.logger.info(f"Updating Guild {guild_name}.")

        url = f"https://api.wynncraft.com/public_api.php?action=guildStats&command={guild_name}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if not response.ok:
                    self.bot.logger.error(f"Failed to fetch from {url}.")
                    return
                else:
                    response = await response.json()

        # Check for error: guild not found
        if response.get("error") == "Guild not found":
            # The guild was deleted, so we add it to deleted_guilds and remove it from guilds
            last_info = self.guild_path().child(guild_name).get().val()
            self.guild_path().child(guild_name).remove()
            last_info['deleted'] = dt.now().timestamp()
            self.deleted_path().child(guild_name).set(last_info)
            return

        # We grab the prefix and additionally add it to a prefix path for faster lookups
        prefix = response['prefix']
        self.prefix_path().child(prefix).set(guild_name)

        # Now we get the members and return a number for change between this and last iteration
        members = map(lambda m: GuildMember.from_data(m).to_dict_item(), response['members'])
        memberdict = dict(members)
        memberdict_old = self.guild_path().child(guild_name).child('members').get().val() or {}
        num_changes = len(memberdict.keys() | memberdict_old.keys()) - len(memberdict.keys() & memberdict_old.keys())
        self.guild_path().child(guild_name).child('members').set(memberdict)

        # Record this update
        if num_changes == 0:
            no_diff_days = self.guild_path().child(guild_name).child('no_diff_days').get().val()
            no_diff_days += 1
        else:
            no_diff_days = 0

        interval = self.guild_path().child(guild_name).child('interval').get().val()
        next_interval = self.calc_next_interval(td(seconds=interval), no_diff_days, num_changes)
        next_update = dt.now() + next_interval

        self.guild_path().child(guild_name).update({
            "interval": next_interval.total_seconds(),
            "no_diff_days": no_diff_days,
            "next_update": next_update.timestamp()
        })

        return next_update.timestamp()

import random
from collections import OrderedDict
from datetime import datetime as dt
from datetime import timedelta as td
from itertools import product
from typing import List, Dict

import discord.app_commands as slash
from discord import Embed
from discord import Interaction
from discord.app_commands import Choice
from discord.utils import escape_markdown
from fuzzywuzzy import fuzz, process

from ..bot import EYESBot, SlashGroup
from ..managers import ConfigManager
from ..utils.paginator import ButtonPaginator


class GuildCommand(SlashGroup, name="guild"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        online = self.command()(self.online)
        online.autocomplete("guild")(self.guild_autocompleter)

        players = self.command()(self.players)
        players.autocomplete("guild")(self.guild_autocompleter)

        playtime = self.command()(self.playtime)
        playtime.autocomplete("guild")(self.guild_autocompleter)

        xp = self.command()(self.xp)
        xp.autocomplete("guild")(self.guild_autocompleter)

    def parse_guild(self, guild_name):
        if ' | ' in guild_name:
            return guild_name.partition(' | ')[2]
        elif guild_name in self.bot.prefixes_manager.g2p:
            return guild_name
        else:
            return self.bot.prefixes_manager.p2g.get(guild_name)

    def parse_guilds(self, guilds_name):
        guilds = ConfigManager.get_dynamic("guildgroups", guilds_name)

        # Not found => Not a group
        if guilds is None:
            # Check if this is a multi-guild search
            if ',' in guilds_name:
                guilds = map(lambda x: x.strip(), guilds_name.split(','))
            else:
                guilds = [guilds_name]

        # Put everything through the parse function
        parsed_guilds = {gu: self.parse_guild(gu) for gu in guilds}
        unparsed_guilds = [k for k, v in parsed_guilds.items() if v is None]
        return parsed_guilds, unparsed_guilds

    async def guild_autocompleter(self, _: Interaction, value: str):
        def generate_letters(letter):
            """A simple function to generate the upper and lower case variants of a letter, in order."""
            if len(letter) != 1 or not letter.isalpha():
                raise ValueError

            if letter.islower():
                return [letter, letter.upper()]
            else:
                return [letter, letter.lower()]

        if len(value) == 0:
            return []

        # We first try and do a case-insensitive guild prefix match if len <= 4
        # by generating all possible combinations of upper/lowercase letters in the prefix
        if len(value) <= 4:
            try:
                possible_letters = map(generate_letters, value)
                possible_words = map(''.join, product(*possible_letters))
            except ValueError:
                prefix_match = []
            else:
                prefix_match = filter(None, map(self.bot.prefixes_manager.p2g.get, possible_words))
        else:
            prefix_match = []

        results = process.extract(value, self.bot.prefixes_manager.g2p.keys(), scorer=fuzz.partial_ratio, limit=25)
        guilds = list(zip(*results))[0]
        guilds = [*prefix_match, *guilds]
        formatted_guilds = [Choice(name=f"{self.bot.prefixes_manager.g2p[gu]} | {gu}", value=gu) for gu in guilds]
        return formatted_guilds[:25]

    @slash.describe(guild="guild to look up")
    async def online(self, ictx: Interaction, guild: str):
        """Lists online players in a guild"""
        parsed = self.parse_guild(guild)

        members = self.bot.guilds_manager.get(parsed)
        online_members = filter(lambda m: m.name in self.bot.players_manager.all, members)
        sorted_members = list(sorted(online_members, key=lambda m: (-m.rank, m.name)))

        embed = Embed(title=f"{self.bot.prefixes_manager.g2p[parsed]} | {parsed}", colour=random.getrandbits(24))

        names = '\n'.join(map(lambda x: x.name, sorted_members)) or '<none>'
        ranks = '\n'.join(map(lambda x: f"{'*' * x.rank:<5s}", sorted_members)) or '<none>'
        worlds = '\n'.join(map(lambda x: self.bot.players_manager.worlds.get(x.name), sorted_members)) or '<none>'
        embed.add_field(name="Username", value=escape_markdown(names), inline=True)
        embed.add_field(name="Rank", value=escape_markdown(ranks), inline=True)
        embed.add_field(name="World", value=escape_markdown(worlds), inline=True)

        await ictx.response.send_message(embed=embed)

    @slash.describe(guild="guild to look up")
    async def players(self, ictx: Interaction, guild: str):
        """Shows information about online players/ranks for a guild"""
        parsed_guilds, unparsed_guilds = self.parse_guilds(guild)

        # Error handling
        if len(unparsed_guilds) == 1:
            await ictx.response.send_message(f"Guild or group `{unparsed_guilds[0]}` not found.")
            return
        elif len(unparsed_guilds) > 1:
            await ictx.response.send_message(f"Guilds `{', '.join(unparsed_guilds)}` not found.")
            return

        await ictx.response.defer()

        # Loop through all the guilds in the search
        ranks: Dict[str, List] = {}
        key_ranks: Dict[str, OrderedDict] = {}
        for guild in parsed_guilds.values():
            # We construct sets for intersection for better time complexity
            members = self.bot.guilds_manager.get(guild)
            online_members = filter(lambda m: m.name in self.bot.players_manager.all, members)

            # This counts how many of each rank are online
            ranks[guild] = [0] * 6
            for member in online_members:
                member_rank = member.rank
                ranks[guild][member_rank] += 1

            key_ranks[guild] = OrderedDict((("Chiefs", ranks[guild][4] + ranks[guild][5]),
                                            ("Strategists", ranks[guild][3]),
                                            ("Captains", ranks[guild][2]),
                                            ("Total", sum(ranks[guild]))))

        # If len == 1, we can use a simple embed field
        if len(parsed_guilds) == 1:
            # Take the key ranks and join strings
            rank_strs = map(lambda x: ': '.join(map(str, x)), key_ranks[guild].items())
            # We want ranks to be in order of high -> low

            # Build an embed
            embed = Embed(title=guild, colour=0xb224ff)
            embed.add_field(name='Online', value='\n'.join(rank_strs), inline=False)
            await ictx.followup.send(embed=embed)

        # Otherwise, we use codeblocks and make a table
        else:
            # Code block formatting
            start_str = "```asciidoc\n Tag  Chief  Strat  Captn  Total\n---------------------------------\n"
            end_str = "\n```"

            # Format it specifically with the tag
            fmt = "{:>4} " + " {:^5} " * 4
            guild_strs = map(lambda gu: fmt.format(self.bot.prefixes_manager.g2p[gu], *key_ranks[gu].values()),
                             key_ranks.keys())

            final_str = start_str + '\n'.join(guild_strs) + end_str
            await ictx.followup.send(final_str)

    @slash.describe(guild="guild to look up",
                    days="how many days of playtime")
    async def playtime(self, ictx: Interaction, guild: str, days: int):
        """Shows the playtime leaderboard of a guild"""
        prev = dt.utcnow() - td(days=days)

        guild = self.parse_guild(guild)

        playtime = await self.bot.db.fetch_tup("""
                SELECT gp.name, SUM(pp.value), EXTRACT(EPOCH FROM MAX(pp.end_time)) 
                FROM guild_player gp
                LEFT JOIN player_playtime pp
                ON gp.guild = %s
                AND gp.name = pp.player
                AND pp.end_time >= %s
                GROUP BY gp.name
        """, (guild, prev))

        playtime.sort(key=lambda x: (-x[1], -x[2], x[0]))

        names, playtimes, seens = zip(*playtime)
        seens = list(map(lambda x: f"<t:{x}:R>" if x >= 0 else "Never", seens))
        playtimes = list(map(lambda x: f"{x // 60}h{x % 60}m", playtimes))
        data = {"Member": names, "Playtime": playtimes, "Last Seen": seens}

        # 24 bit colour
        paginator = ButtonPaginator(ictx, f"{guild} {days}d Playtime", data, colour=random.getrandbits(24), text='')

        await paginator.generate_embed().respond()

    @slash.describe(guild="guild to look up",
                    days="how many days of xp generation")
    async def xp(self, ictx: Interaction, guild: str, days: int):
        """ Shows an XP leaderboard for individual members in a guild. """
        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        guild = self.parse_guild(guild)

        # Get xp
        # TODO: also fix this with start/end times
        xp_res = await self.bot.db.fetch_tup("SELECT gp.name, sum(px.value) FROM player_xp px "
                                             "LEFT JOIN guild_player gp ON gp.uuid = px.uuid AND gp.guild = px.guild "
                                             "AND px.guild = %s AND px.time >= %s "
                                             "GROUP BY gp.name "
                                             "ORDER BY sum(px.value) DESC",
                                             (guild, prev))

        members, xp_gained = zip(*xp_res)

        # Sort into dict
        data = {"Member": members, "XP": xp_gained}
        paginator = ButtonPaginator(ictx, f"{guild} {days} Day XP Gains", data, colour=random.getrandbits(24), text='')

        await paginator.generate_embed().respond()

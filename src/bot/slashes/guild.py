import random
import time
from collections import OrderedDict
from datetime import datetime as dt
from itertools import product
from typing import List, Dict

from discord import ApplicationContext, Option, OptionChoice
from discord import Embed
from discord.utils import escape_markdown
from fuzzywuzzy import fuzz, process

from ..bot import EYESBot, SlashCommand
from ..managers import ConfigManager
from ..utils.paginator import ButtonPaginator


class GuildCommand(SlashCommand, name="guild"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.group = self.bot.bot.create_group(
            "guild", "No Description", guild_ids=self.guild_ids
        )

        online = self.group.command()(self.online)
        online.options[0].autocomplete = self.guild_autocompleter

        players = self.group.command()(self.players)
        players.options[0].autocomplete = self.guild_autocompleter

        playtime = self.group.command()(self.playtime)
        playtime.options[0].autocomplete = self.guild_autocompleter

    def parse_guild(self, guild_name):
        if ' | ' in guild_name:
            return guild_name.partition(' | ')[2]
        elif guild_name in self.bot.prefixes.g2p:
            return guild_name
        else:
            return self.bot.prefixes.p2g.get(guild_name)

    def parse_guilds(self, guilds_name):
        guilds = ConfigManager.get("guildgroups", guilds_name)

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

    async def guild_autocompleter(self, ctx: ApplicationContext):
        def generate_letters(letter):
            """A simple function to generate the upper and lower case variants of a letter, in order."""
            if len(letter) != 1 or not letter.isalpha():
                raise ValueError

            if letter.islower():
                return [letter, letter.upper()]
            else:
                return [letter, letter.lower()]

        if len(ctx.value) == 0:
            return []

        # We first try and do a case-insensitive guild prefix match if len <= 4
        # by generating all possible combinations of upper/lowercase letters in the prefix
        if len(ctx.value) <= 4:
            try:
                possible_letters = map(generate_letters, ctx.value)
                possible_words = map(''.join, product(*possible_letters))
            except ValueError:
                prefix_match = []
            else:
                prefix_match = filter(None, map(self.bot.prefixes.p2g.get, possible_words))
        else:
            prefix_match = []

        results = process.extract(ctx.value, self.bot.prefixes.g2p.keys(), scorer=fuzz.partial_ratio, limit=25)
        guilds = list(zip(*results))[0]
        guilds = [*prefix_match, *guilds]
        formatted_guilds = [OptionChoice(f"{self.bot.prefixes.g2p[gu]} | {gu}", gu) for gu in guilds]
        return formatted_guilds

    async def online(
            self, _, ctx: ApplicationContext,
            guild: Option(str, "gild to look up")
    ):
        """Lists online players in a guild"""
        parsed = self.parse_guild(guild)

        members = self.bot.guilds.get(parsed)
        online_members = filter(lambda m: m.name in self.bot.players.all, members)
        sorted_members = list(sorted(online_members, key=lambda m: (-m.rank, m.name)))

        embed = Embed(title=f"{self.bot.prefixes.g2p[parsed]} | {parsed}", colour=random.getrandbits(24))

        if online_members:
            names = '\n'.join(map(lambda x: x.name, sorted_members))
            ranks = '\n'.join(map(lambda x: f"{'*' * x.rank:<5s}", sorted_members))
            worlds = '\n'.join(map(lambda x: self.bot.players.worlds.get(x.name), sorted_members))
            embed.add_field(name="Username", value=escape_markdown(names), inline=True)
            embed.add_field(name="Rank", value=escape_markdown(ranks), inline=True)
            embed.add_field(name="World", value=escape_markdown(worlds), inline=True)

        await ctx.respond(embed=embed)

    async def players(
            self, _, ctx: ApplicationContext,
            guild: Option(str, "guild to look up")
    ):
        """Shows information about online players/ranks for a guild"""
        parsed_guilds, unparsed_guilds = self.parse_guilds(guild)

        # Error handling
        if len(unparsed_guilds) == 1:
            await ctx.respond(f"Guild or group `{unparsed_guilds[0]}` not found.")
            return
        elif len(unparsed_guilds) > 1:
            await ctx.respond(f"Guilds `{', '.join(unparsed_guilds)}` not found.")
            return

        await ctx.defer()

        # Loop through all the guilds in the search
        ranks: Dict[str, List] = {}
        key_ranks: Dict[str, OrderedDict] = {}
        for guild in parsed_guilds.values():
            # We construct sets for intersection for better time complexity
            members = self.bot.guilds.get(guild)
            online_members = filter(lambda m: m.name in self.bot.players.all, members)

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
            await ctx.send_followup(embed=embed)

        # Otherwise, we use codeblocks and make a table
        else:
            # Code block formatting
            start_str = "```asciidoc\n Tag  Chief  Strat  Captn  Total\n---------------------------------\n"
            end_str = "\n```"

            # Format it specificallywith the tag
            fmt = "{:>4} " + " {:^5} " * 4
            guild_strs = map(lambda gu: fmt.format(self.bot.prefixes.g2p[gu], *key_ranks[gu].values()),
                             key_ranks.keys())

            final_str = start_str + '\n'.join(guild_strs) + end_str
            await ctx.send_followup(final_str)

    async def playtime(
            self, _, ctx: ApplicationContext,
            guild: Option(str, "guild to look up"),
            days: Option(int, "how many days of playtime")
    ):
        """Shows the playtime leaderboard of a guild"""
        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        guild = self.parse_guild(guild)
        members = self.bot.guilds.get(guild)
        playtime = []

        total = len(members)
        await ctx.respond("Fetching data...")
        start = time.time()

        for i, member in enumerate(members):
            # Progress bar
            if time.time() - start > 5:
                start = time.time()
                await ctx.edit(content=f"Fetching data... ({i}/{total})")

            # We default to empty dict as otherwise it might be an empty list
            self.bot.db.path = None
            online_times = self.bot.db.child('wynncraft').child('playtime').child('players').child(member.name) \
                               .order_by_key().start_at(str(prev)).end_at(str(now)).get().val() or {}
            member_playtime = int(sum(online_times.values()))

            all_times = map(int, self.bot.db.child('wynncraft').child('playtime').child('players').child(member.name)
                            .shallow().get().val() or [-1])
            last_seen = max(all_times)
            playtime.append((member.name, member_playtime, last_seen))

        playtime.sort(key=lambda x: (-x[1], -x[2], x[0]))

        names, playtimes, seens = zip(*playtime)
        seens = list(map(lambda x: f"<t:{x}:R>" if x >= 0 else "Never", seens))
        playtimes = list(map(lambda x: f"{x // 60}h{x % 60}m", playtimes))
        data = {"Member": names, "Playtime": playtimes, "Last Seen": seens}

        # 24 bit colour
        paginator = ButtonPaginator(ctx, f"{guild} {days}d Playtime", data, colour=random.getrandbits(24), text='')

        await paginator.generate_embed().respond()

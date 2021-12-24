from itertools import product
from typing import List

from discord import ApplicationContext, Option, OptionChoice, Embed
from fuzzywuzzy import fuzz, process

from ..bot import EYESBot, SlashCommand
from ..utils.wynn import RANKS

class GuildCommand(SlashCommand, name="guild"):
    def __init__(self, bot: EYESBot, guild_ids: List[int]):
        super().__init__(bot, guild_ids)

        self.group = self.bot.bot.create_group(
            "guild", "No Description", guild_ids=self.guild_ids
        )

        info = self.group.command()(self.info)
        info.options[0].autocomplete = self.info_autocompleter

    async def info_autocompleter(self, ctx: ApplicationContext):
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
            except ValueError:
                prefix_match = []
            else:
                possible_words = map(''.join, product(*possible_letters))
                prefix_match = filter(None, map(self.bot.prefixes.p2g.get, possible_words))
        else:
            prefix_match = []

        results = process.extract(ctx.value, self.bot.prefixes.g2p.keys(), scorer=fuzz.partial_ratio, limit=25)
        guilds = list(zip(*results))[0]
        guilds = [*prefix_match, *guilds]
        formatted_guilds = [OptionChoice(f"{self.bot.prefixes.g2p[gu]} | {gu}", gu) for gu in guilds]
        return formatted_guilds

    async def info(
            self, ctx: ApplicationContext,
            guild: Option(str, "guild to look up")
    ):
        # Store a copy of the original argument
        _guild = guild
        if ' | ' in guild:
            guild = guild.partition(' | ')[2]
        elif guild not in self.bot.prefixes.g2p:
            guild = self.bot.prefixes.p2g.get(guild)

        if not guild:
            await ctx.respond(f"Guild `{_guild}` not found.")
            return

        # We construct sets for intersection for better time complexity
        members = self.bot.guilds.get(guild)
        online_players = self.bot.players.players
        online_members = set(m.name for m in members) & set(online_players)
        online_guildmembers = filter(lambda m: m.name in online_members, members)

        # This counts how many of each rank are online
        ranks = [0] * 6
        for member in online_guildmembers:
            member_rank = member.rank
            ranks[member_rank] += 1
        total = sum(ranks)
        # Convert it to a (rank_name, online_count) list
        ranks = zip(map(lambda r: r.title(), RANKS), ranks)
        # and join each one to make a string
        rank_strs = map(lambda x: f"{x[0]}: {x[1]}", ranks)
        total_str = f"__Total__: {total}"

        # Build an embed
        embed = Embed(title=guild, colour=0xb224ff)
        embed.add_field(name='Online', value='\n'.join([*rank_strs, total_str]), inline=False)
        await ctx.respond(embed=embed)

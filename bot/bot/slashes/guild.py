from itertools import product
from typing import List

from discord import ApplicationContext, Option, OptionChoice
from fuzzywuzzy import fuzz, process

from ..bot import EYESBot, SlashCommand


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

        members = self.bot.guilds.get(guild)
        member_names = set(m.name for m in members)
        online_players = set(self.bot.players.players)
        online_members = member_names & online_players
        await ctx.respond('\n'.join(online_members))

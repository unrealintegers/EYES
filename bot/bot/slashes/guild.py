from collections import OrderedDict
from itertools import product
from typing import List, Dict

from discord import ApplicationContext, Option, OptionChoice, Embed
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

    async def info(
            self, ctx: ApplicationContext,
            guild: Option(str, "guild to look up")
    ):
        def parse_guild(guild_name):
            if ' | ' in guild_name:
                return guild_name.partition(' | ')[2]
            elif guild_name in self.bot.prefixes.g2p:
                return guild_name
            else:
                return self.bot.prefixes.p2g.get(guild_name)

        # guildgroup = start with $
        if guild[0] == '$':
            groups = self.bot.db.child("config").child("global").child("guildgroups").get().val()
            guilds = groups.get(guild[1:])
            if guilds is None:
                await ctx.respond(f"Guild group `{guild[1:]}` not found.")
                return
        else:
            # Check if this is a multi-guild search
            if ',' in guild:
                guilds = map(lambda x: x.strip(), guild.split(','))
            else:
                guilds = [guild]

        # Put everything through the parse function
        parsed_guilds = {gu: parse_guild(gu) for gu in guilds}
        unparsed_guilds = [k for k, v in parsed_guilds.items() if v is None]

        # Error handling
        if len(unparsed_guilds) == 1:
            await ctx.respond(f"Guild `{unparsed_guilds[0]}` not found.")
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
            online_players = self.bot.players.players
            online_members = set(m.name for m in members) & set(online_players)
            online_guildmembers = filter(lambda m: m.name in online_members, members)

            # This counts how many of each rank are online
            ranks[guild] = [0] * 6
            for member in online_guildmembers:
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
            await ctx.respond(embed=embed)

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
            await ctx.respond(final_str)

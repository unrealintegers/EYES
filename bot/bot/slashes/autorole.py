from ..bot import SlashCommand, EYESBot
from ..utils.autorolewizard import AutoroleWizard

from discord import ApplicationContext
from discord import Member
from discord import Permissions


class AutoroleCommand(SlashCommand, name="autorole", permissions=Permissions(manage_roles=True, manage_messages=True)):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.group = self.bot.bot.create_group(
            "autorole", "No Description", guild_ids
        )
        self.group.default_permission = False

        self.group.command()(self.create)

    async def create(
            self, ctx: ApplicationContext
    ):
        """Creates a new autorole message."""

        await ctx.defer()
        if not isinstance(ctx.author, Member):
            await ctx.respond("Cannot be used in a DM!")
            return

        await AutoroleWizard.new(self.bot, ctx.author, ctx.channel)
        await ctx.delete()

from ..bot import SlashCommand, EYESBot
from ..utils.autorolewizard import AutoroleWizard

from discord import ApplicationContext, Option
from discord import Member
from discord import NotFound, HTTPException


class AutoroleCommand(SlashCommand, name="autorole"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.group = self.bot.bot.create_group(
            "autorole", "No Description", guild_ids
        )
        self.group.default_permission = False

        self.group.command()(self.create)
        self.group.command()(self.edit)

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

    async def edit(
            self, ctx: ApplicationContext,
            message: Option(int, "message_id of message")
    ):
        await ctx.defer()
        try:
            original = await ctx.channel.fetch_message(message)
            await AutoroleWizard.from_msg(self.bot, ctx.author, ctx.channel, original)
        except (NotFound, HTTPException):
            await ctx.respond("Message not found!", ephemeral=True)
        finally:
            await ctx.delete()

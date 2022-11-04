from discord import Interaction, TextChannel, Permissions
from discord import NotFound, HTTPException
import discord.app_commands as slash

from ..bot import SlashGroup, EYESBot
from ..utils.autorolewizard import AutoroleWizard


class AutoroleCommand(SlashGroup, name="autorole", guild_only=True, default_permissions=Permissions()):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.command()(self.create)
        self.command()(self.edit)

    async def create(
            self, ictx: Interaction
    ):
        """Creates a new autorole message."""

        await ictx.response.defer(ephemeral=True)

        if not isinstance(ictx.channel, TextChannel):
            await ictx.edit_original_response(content="Can only be used in text channels!")
            return

        ar = await AutoroleWizard.new(self.bot, ictx.user, ictx.channel)
        await ictx.edit_original_response(content=ar.thread.mention)

    @slash.describe(channel="channel_id of message", message="message_id of message")
    async def edit(
            self, ictx: Interaction,
            channel: str, message: str
    ):
        """Edits an existing autorole message."""
        await ictx.response.defer(ephemeral=True)

        if not isinstance(ictx.channel, TextChannel):
            await ictx.edit_original_response(content="Command can only be used in Text Channels.")
            return

        if not message.isdecimal():
            await ictx.edit_original_response(content="Message must be an integer!")
            return

        try:
            origch = await ictx.guild.fetch_channel(int(channel))
            original = await origch.fetch_message(int(message))
        except (NotFound, HTTPException):
            await ictx.edit_original_response(content="Message not found!")
        else:
            ar = await AutoroleWizard.from_msg(self.bot, ictx.user, ictx.channel, original)
            await ictx.edit_original_response(content=ar.thread.mention)

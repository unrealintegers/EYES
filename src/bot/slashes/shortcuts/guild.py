from discord import Interaction
import discord.app_commands as slash

from ..guild import GuildCommand
from ...bot import EYESBot, SlashCommand


class GuildShortcutCommand(GuildCommand, SlashCommand, name="g"):
    LOOKUP_DICT = {
        'o': GuildCommand.online,
        'p': GuildCommand.players
    }

    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        SlashCommand.__init__(self, bot, guild_ids)

    @slash.describe(cmd="shortcut command to execute")
    async def callback(self, ictx: Interaction, cmd: str):
        """A shortcut to run various /guild commands"""
        command, guild = cmd.split()
        if command not in self.LOOKUP_DICT:
            await ictx.response.send_message("Command not found!", ephemeral=True)
            return

        callback = self.LOOKUP_DICT[command]
        await callback(self, ictx, guild)

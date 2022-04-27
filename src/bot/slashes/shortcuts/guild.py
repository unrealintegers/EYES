from discord import ApplicationContext, Option

from ..guild import GuildCommand
from ...bot import EYESBot, SlashCommand


class GuildShortcutCommand(GuildCommand, SlashCommand, name="g"):
    LOOKUP_DICT = {
        'o': GuildCommand.online,
        'p': GuildCommand.players
    }

    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        SlashCommand.__init__(self, bot, guild_ids)

        self.register(self.callback)

    async def callback(self, ctx: ApplicationContext,
                       cmd: Option(str, "Shortcut command to execute")):
        """A shortcut to run various /guild commands"""
        command, guild = cmd.split()
        if command not in self.LOOKUP_DICT:
            await ctx.respond("Command not found!", ephemeral=True)
            return

        callback = self.LOOKUP_DICT[command]
        await callback(self, ctx, guild)

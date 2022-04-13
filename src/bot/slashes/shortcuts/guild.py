from ..bot import EYESBot, SlashCommand

from discord import ApplicationContext, Option


class GuildShortcutCommand(SlashCommand):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    def callback(self, ctx: ApplicationContext,
                 cmd: Option(str, "shortcut command", True)):
        command, *args = cmd.split()

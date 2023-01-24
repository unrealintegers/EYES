import typing

from discord import Interaction, Permissions
from discord.app_commands import Choice
import discord.app_commands as slash

if typing.TYPE_CHECKING:
    from .bot import EYESBot


class SlashCommand:
    # Dynamic Parameters
    def __init__(self, bot: "EYESBot", guild_ids: list[int]):
        self.bot = bot

        self._command = bot.tree.command(name=self.__name, guilds=guild_ids)(self.callback)  # type: ignore
        self._command.default_permissions = self.__permissions
        self._command.guild_only = self.__guild_only

    # Static Parameters
    def __init_subclass__(cls, *,
                          name: str = None,
                          default_permissions: Permissions = None,
                          guild_only: bool = False,
                          **kwargs):
        cls.__name = name or cls.__name__.lower()
        cls.__permissions = default_permissions
        cls.__guild_only = guild_only

    # Override in Subclass
    async def callback(self, ictx: Interaction, *args):
        pass


class SlashGroup(slash.Group):
    # Dynamic Parameters
    def __init__(self, bot: "EYESBot", guild_ids: list[int]):
        super().__init__(guild_ids=guild_ids)

        self.bot = bot
        bot.tree.add_command(self)

    # Static Parameters
    def __init_subclass__(cls, *,
                          name: str = None,
                          **kwargs):
        name = name or cls.__name__.lower()

        # Description does not matter for Command Groups
        super().__init_subclass__(name=name, description="<None>", **kwargs)


class ContextMenuCommand:
    # Dynamic Parameters
    def __init__(self, bot: "EYESBot", guild_ids: list[int]):
        self.bot = bot

        self._command = bot.tree.context_menu(name=self.__name, guilds=guild_ids)(self.callback)  # type: ignore
        self._command.default_permissions = self.__permissions
        self._command.guild_only = self.__guild_only

    # Static Parameters
    def __init_subclass__(cls, *,
                          name: str = None,
                          default_permissions: Permissions = None,
                          guild_only: bool = False,
                          **kwargs):
        cls.__name = name or cls.__name__.lower()
        cls.__permissions = default_permissions
        cls.__guild_only = guild_only

    # Override in Subclass
    async def callback(self, ictx: Interaction, message_or_user):
        pass


class BotTask:
    def __init__(self, bot: "EYESBot"):
        self.bot = bot


class WynncraftAPI:
    TERRITORIES = r"https://api.wynncraft.com/public_api.php?action=territoryList"


def choice(name):
    return Choice(name=name, value=name)

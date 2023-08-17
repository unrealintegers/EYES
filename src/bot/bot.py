from __future__ import annotations

import logging

from discord import Intents
from discord.ext import commands

from .listeners import InteractionListener, MessageListener
from .managers import ConfigManager, GuildPrefixManager, GuildMemberManager, PlayerManager, MapManager
from .models import SlashCommand, ContextMenuCommand, BotTask, SlashGroup
from .utils.db import DatabaseManager


class EYESBot(commands.Bot):
    def __init__(self, prefix: str):
        super().__init__(command_prefix=prefix,
                         intents=Intents.all(),
                         auto_sync_commands=False)
        self.remove_command('help')

        # Setup logging
        self.logger = logging.getLogger('EYES')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(f"< %(asctime)s | EYES | %(levelname)4.4s > %(message)s ",
                                               datefmt="%y-%m-%d %H:%M:%S"))
        self.logger.addHandler(handler)

        # Create managers
        self.db: DatabaseManager = DatabaseManager()

        self.guilds_manager = GuildMemberManager(self)
        self.prefixes_manager = GuildPrefixManager(self)
        self.players_manager = PlayerManager(self)
        self.map_manager = MapManager(self)
        self.reaction = InteractionListener(self)
        self.msg = MessageListener(self)

        self.tasks: dict[str, BotTask] = {}

        ConfigManager.update()

    async def instantiate_commands(self):
        # guild_dict = ConfigManager.get_static("application")

        for sub_cls in SlashCommand.__subclasses__():
            # name = sub_cls.name  # noqa : name is guaranteed to be defined
            # guild_ids = guild_dict.pop(name, {})  # {} = global

            # sub_cls(self, list(guild_ids.keys()) or None)  # {} -> None = global

            sub_cls(self, [])

        for sub_cls in SlashGroup.__subclasses__():
            sub_cls(self, [])

        for sub_cls in ContextMenuCommand.__subclasses__():
            sub_cls(self, [])

        # if guild_dict:
        #     self.logger.info("Unregistered Commands: {guild_dict}")

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks[sub_cls.__name__] = sub_cls(self)

            await self.tasks[sub_cls.__name__].init()

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name}#{self.user.discriminator}")

        await self.db.init()

        self.prefixes_manager.start()
        self.guilds_manager.start()
        self.map_manager.init()
        await self.msg.update_replacements()

        await self.instantiate_commands()
        await self.add_tasks()

        await self.tree.sync()

        self.logger.info("Synced")

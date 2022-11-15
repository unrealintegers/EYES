from __future__ import annotations

import json
import logging
import os

import pyrebase as pyrebase4
from discord import Intents
from discord.ext import commands

from .listeners import InteractionListener
from .managers import ConfigManager, GuildPrefixManager, GuildMemberManager, PlayerManager
from .models import SlashCommand, BotTask, SlashGroup


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
        self.guilds_manager = GuildMemberManager(self)
        self.prefixes_manager = GuildPrefixManager(self)
        self.players_manager = PlayerManager(self)
        self.reaction = InteractionListener(self)

        self.tasks: dict[str, BotTask] = {}

        # Using env variable as Heroku expects
        firebase = pyrebase4.initialize_app(json.loads(os.getenv("DB_CREDS")))
        self.db = firebase.database()

        ConfigManager.init_db(self.db)

    async def instantiate_commands(self):
        guild_dict = self.db.child("application").child("commands").get().val()

        for sub_cls in SlashCommand.__subclasses__():
            # name = sub_cls.name  # noqa : name is guaranteed to be defined
            # guild_ids = guild_dict.pop(name, {})  # {} = global

            # sub_cls(self, list(guild_ids.keys()) or None)  # {} -> None = global

            sub_cls(self, [])

        for sub_cls in SlashGroup.__subclasses__():
            sub_cls(self, [])

        # if guild_dict:
        #     self.logger.info("Unregistered Commands: {guild_dict}")

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks[sub_cls.__name__] = sub_cls(self)

    async def on_ready(self):
        self.logger.info(f"Logged in as {self.user.name}#{self.user.discriminator}")

        self.players_manager.run()
        self.prefixes_manager.start()

        await self.instantiate_commands()
        await self.add_tasks()

        await self.tree.sync()

        self.logger.info("Synced")

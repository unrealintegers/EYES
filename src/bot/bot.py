from __future__ import annotations

import json
import logging
import os

import pyrebase as pyrebase4
from discord import Intents, Permissions
from discord.ext import commands

from .listeners import ReactionListener
from .managers import ConfigManager, GuildPrefixManager, GuildMemberManager, PlayerManager


class SlashCommand:
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        self.bot = bot
        self.guild_ids = guild_ids

    def __init_subclass__(cls, *,
                          name: str = None,
                          permissions: Permissions = None,
                          **kwargs):
        cls.name = name or cls.__name__.lower()

    def register(self, coro, *, name=None):
        if not name:
            name = self.name
        self.bot.bot.slash_command(name=name, guild_ids=self.guild_ids)(coro)


class BotTask:
    def __init__(self, bot: EYESBot):
        self.bot = bot


class EYESBot:
    def __init__(self, prefix: str):
        self.bot = commands.Bot(command_prefix=prefix,
                                intents=Intents.all(),
                                auto_sync_commands=False)
        self.bot.remove_command('help')

        # Setup logging
        self.logger = logging.Logger('main')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s", "%m/%d %H:%M:%S"))
        self.logger.addHandler(handler)

        # Create managers
        self.guilds = GuildMemberManager(self)
        self.prefixes = GuildPrefixManager(self)
        self.players = PlayerManager(self)
        self.reaction = ReactionListener(self)

        self.tasks: dict[str, BotTask] = {}

        # Using env variable as Heroku expects
        firebase = pyrebase4.initialize_app(json.loads(os.getenv("DB_CREDS")))
        self.db = firebase.database()

        ConfigManager.init_db(self.db)

        self.bot.add_listener(self.on_ready)

    async def instantiate_commands(self):
        guild_dict = self.db.child("application").child("commands").get().val()

        for sub_cls in SlashCommand.__subclasses__():
            name = sub_cls.name  # noqa : name is guaranteed to be defined
            guild_ids = guild_dict.pop(name, {})  # {} = global

            sub_cls(self, list(guild_ids.keys()) or None)  # {} -> None = global

        if guild_dict:
            self.logger.info("Unregistered Commands: {guild_dict}")

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks[sub_cls.__name__] = sub_cls(self)

    async def on_ready(self):
        self.logger.info("Connected")

        self.players.run()

        await self.instantiate_commands()
        await self.add_tasks()

        await self.bot.sync_commands()

        self.logger.info("Synced")

    def run(self):
        self.bot.run(os.getenv("TOKEN"))

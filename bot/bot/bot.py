from __future__ import annotations

import json
import logging
import os
from typing import List

import discord
import pyrebase
from discord.ext import commands

from .utils.wynn import GuildMemberManager, GuildPrefixManager, PlayerManager
from .managers import ConfigManager

class SlashCommand:
    def __init__(self, bot: EYESBot, guild_ids: List[int]):
        self.bot = bot
        self.guild_ids = guild_ids

    def __init_subclass__(cls, **kwargs):
        if 'name' in kwargs:
            cls.name = kwargs['name']
        else:
            cls.name = cls.__name__.lower()

    def register(self, coro, *, name=None):
        if not name:
            name = coro.__name__
        self.bot.bot.slash_command(guild_ids=self.guild_ids, name=name)(coro)


class BotTask:
    def __init__(self, bot: EYESBot):
        self.bot = bot


class EYESBot:
    def __init__(self, prefix: str):
        self.bot = commands.Bot(command_prefix=prefix,
                                intents=discord.Intents.all())
        self.bot.remove_command('help')

        # Setup logging
        self.logger = logging.Logger('main')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s", "%m/%d %H:%M:%S"))
        self.logger.addHandler(handler)

        self.guilds = GuildMemberManager(self)
        self.prefixes = GuildPrefixManager(self)
        self.players = PlayerManager()

        self.tasks: List[BotTask] = []

        # Using env variable as Heroku expects
        firebase = pyrebase.initialize_app(json.loads(os.getenv("DB_CREDS")))
        self.db = firebase.database()

        ConfigManager.init_db(self.db)

        self.bot.add_listener(self.on_ready)

    async def instantiate_commands(self, cmd_dict):
        for sub_cls in SlashCommand.__subclasses__():
            name = sub_cls.name  # noqa : name is guaranteed to be defined
            guild_ids = cmd_dict.pop(name, None)  # None = global
            sub_cls(self, guild_ids)

        if cmd_dict:
            print(f"Unregistered Commands: {cmd_dict}")

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks.append(sub_cls(self))

    def run(self):
        self.bot.run(os.getenv("TOKEN"))

    async def on_ready(self):
        self.logger.info("Connected")

        self.players.run()

        await self.instantiate_commands({})  # TODO: Setup command dict in DB
        await self.bot.register_commands()

        await self.add_tasks()

        self.logger.info("Synced")

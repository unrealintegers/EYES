from __future__ import annotations

import json
import logging
import os
from typing import Optional

from discord import Role
from discord import Intents, Permissions, CommandPermission
import pyrebase as pyrebase4
from discord.ext import commands

from .managers import ConfigManager, GuildPrefixManager, GuildMemberManager, PlayerManager
from .listeners import ReactionListener


class SlashCommand:
    def __init__(self, bot: EYESBot, guild_ids: list[int], permissions: Optional[list[CommandPermission]]):
        self.bot = bot
        self.guild_ids = guild_ids
        self.permissions = permissions

    def __init_subclass__(cls, *,
                          name: str = None,
                          required_permission: Permissions = None,
                          **kwargs):
        cls.name = name or cls.__name__.lower()
        cls.permissions = required_permission

    @classmethod
    def generate_permissions(cls, role_list: dict[int, list[Role]]):
        if cls.permissions is None:  # noqa: permissions is always defined
            return []

        permissions = []
        for guild_id, roles in role_list.items():
            for role in roles:
                if cls.permissions.is_subset(role.permissions):  # noqa: permissions is always defined
                    permissions.append(CommandPermission(role.id, 1, True, guild_id))
        return permissions

    def register(self, coro, *, name=None):
        if not name:
            name = coro.__name__
        self.bot.bot.slash_command(name=name, guild_ids=self.guild_ids, permissions=self.permissions)(coro)


class BotTask:
    def __init__(self, bot: EYESBot):
        self.bot = bot


class EYESBot:
    def __init__(self, prefix: str):
        self.bot = commands.Bot(command_prefix=prefix,
                                intents=Intents.all())
        self.bot.remove_command('help')

        # Setup logging
        self.logger = logging.Logger('main')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s", "%m/%d %H:%M:%S"))
        self.logger.addHandler(handler)

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

    async def instantiate_commands(self, cmd_dict):
        role_list = {}
        for guild in self.bot.guilds:
            role_list[guild.id] = await guild.fetch_roles()

        for sub_cls in SlashCommand.__subclasses__():
            name = sub_cls.name  # noqa : name is guaranteed to be defined
            guild_ids = cmd_dict.pop(name, None)  # None = global
            permissions = sub_cls.generate_permissions(role_list)

            sub_cls(self, guild_ids, permissions)

        if cmd_dict:
            print(f"Unregistered Commands: {cmd_dict}")

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks[sub_cls.__name__] = sub_cls(self)

    def run(self):
        self.bot.run(os.getenv("TOKEN"))

    async def on_ready(self):
        self.logger.info("Connected")

        self.players.run()

        await self.instantiate_commands({})  # TODO: Setup command dict in DB
        await self.bot.register_commands()

        await self.add_tasks()

        self.logger.info("Synced")

from __future__ import annotations

import json
import logging
import os

from discord import Intents, Permissions
import pyrebase as pyrebase4
from discord.ext import commands
from discord.utils import find

from .managers import ConfigManager, GuildPrefixManager, GuildMemberManager, PlayerManager
from .listeners import ReactionListener


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

    async def instantiate_commands(self):
        guild_dict = self.db.child("application").child("commands").get().val()

        for sub_cls in SlashCommand.__subclasses__():
            name = sub_cls.name  # noqa : name is guaranteed to be defined
            guild_ids = guild_dict.pop(name, {})  # {} = global

            sub_cls(self, list(guild_ids.keys()) or None)  # {} -> None = global

        if guild_dict:
            print(f"Unregistered Commands: {guild_dict}")

    async def process_permissions(self):
        perms_dict = self.db.child("application").child("permissions").get().val()

        for guild_id, d1 in perms_dict.items():
            guild_permissions = []
            for command_name, d2 in d1.items():
                command_id = find(lambda c: c[1].name == command_name, self.bot._application_commands.items())[0]
                command_permissions = []

                for role_id, permission in d2.items():
                    command_permissions.append({
                        "id": role_id,
                        "type": 1,
                        "permission": permission
                    })

                guild_permissions.append({
                    "id": command_id,
                    "permissions": command_permissions
                })

            await self.bot.http.bulk_edit_guild_application_command_permissions(
                self.bot.application_id, guild_id, guild_permissions
            )

    async def add_tasks(self):
        for sub_cls in BotTask.__subclasses__():
            self.tasks[sub_cls.__name__] = sub_cls(self)

    def run(self):
        self.bot.run(os.getenv("TOKEN"))

    async def on_ready(self):
        self.logger.info("Connected")

        self.players.run()

        await self.instantiate_commands()  # TODO: Setup command dict in DB
        await self.add_tasks()

        await self.bot.sync_commands()
        # await self.process_permissions()



        self.logger.info("Synced")

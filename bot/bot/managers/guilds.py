from __future__ import annotations

import typing
from typing import Set

import aiocron
from pytz import utc

from ..utils.wynn import GuildMember

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class GuildMemberManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

    def path(self):
        return self.bot.db.child('wynncraft').child('guilds')

    def get(self, guild_name) -> Set[GuildMember]:
        members = self.path().child(guild_name).child('members').get().val() or []
        return set(GuildMember(uuid=k, **v) for k, v in members.items())


class GuildPrefixManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot
        self.p2g = {}
        self.g2p = {}

        self.update().call_func()
        self.update().start()

    def path(self):
        return self.bot.db.child('wynncraft').child('prefixes')

    def update(self):
        @aiocron.crontab("5 * * * *", start=False, tz=utc)
        async def wrapper():
            self.p2g = self.path().get().val()
            self.g2p = {v: k for k, v in self.p2g.items()}

        return wrapper

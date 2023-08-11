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

    def get(self, guild_name, raw=False) -> Set[GuildMember] | dict[str, dict]:
        members = self.bot.db.fetch_dict("SELECT * FROM guild_player "
                                         "WHERE guild = %s", (guild_name, ))
        if raw:
            return members
        else:
            return set(GuildMember(**m) for m in members)


class GuildPrefixManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot
        self.p2g = {}
        self.g2p = {}

    def start(self):
        self.update().call_func()
        self.update().start()

    def update(self):
        @aiocron.crontab("5 * * * *", start=False, tz=utc)
        async def wrapper():
            tups = self.bot.db.fetch_tup("SELECT name, prefix FROM guild_info")
            self.p2g = {p: g for g, p in tups}
            self.g2p = {g: p for g, p in tups}

        return wrapper

from __future__ import annotations

import asyncio
import typing
from datetime import datetime as dt
from typing import Set

import aiocron
import aiohttp
from dateutil import parser as dtparser
from pytz import utc

if typing.TYPE_CHECKING:
    from ..bot import EYESBot

RANKS = [
    'RECRUIT',
    'RECRUITER',
    'CAPTAIN',
    'STRATEGIST',
    'CHIEF',
    'OWNER'
]


class GuildMember:
    def __init__(self,
                 uuid: str,
                 name: str,
                 rank: int,
                 joined: float | dt,
                 contributed: int,
                 **_):
        self.uuid = uuid
        self.name = name
        self.rank = rank
        if isinstance(joined, dt):
            self.joined = joined
        else:
            self.joined = dt.utcfromtimestamp(joined)
        self.contributed = contributed

    @classmethod
    def from_data(cls, data):
        if data['rank']:
            data['rank'] = RANKS.index(data['rank'])
        if data['joined']:
            data['joined'] = dtparser.parse(data['joined'])
        return cls(**data)

    # uuid -> { name, rank: int, joined: float (timestamp), contributed: int }
    def to_dict_item(self):
        k = self.uuid
        v = vars(self)
        del v['uuid']
        v['joined'] = v['joined'].timestamp()
        return k, v


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


class PlayerManager:
    def __init__(self):
        self.players = []

    def run(self):
        asyncio.create_task(self.update())

    async def update(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.wynncraft.com/public_api.php?action=onlinePlayers") as response:
                if not response.ok:
                    return

                players = await response.json()

        del players['request']
        self.players = sum(players.values(), [])

        await asyncio.sleep(30)
        asyncio.create_task(self.update())

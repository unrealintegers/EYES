from __future__ import annotations

import typing
from itertools import groupby
from operator import itemgetter

from discord.ext import tasks

from ..utils.wynn import GuildMember

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class GuildMemberManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.g2m = {}
        self.m2g = {}

    @tasks.loop(hours=4)
    async def update(self):
        members = await self.bot.db.fetch_dict("SELECT * FROM guild_player ORDER BY guild")
        self.g2m = {g: set(GuildMember(**m) for m in ms)
                    for g, ms in groupby(members, key=itemgetter('guild'))}
        self.m2g = {m['name']: m['guild'] for m in members}


class GuildPrefixManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot
        self.p2g = {}
        self.g2p = {}

    @tasks.loop(hours=1)
    async def update(self):
        tups = await self.bot.db.fetch_tup("SELECT name, prefix FROM guild_info")
        self.p2g = {p: g for g, p in tups}
        self.g2p = {g: p for g, p in tups}

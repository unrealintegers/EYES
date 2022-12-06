from __future__ import annotations

import asyncio
from datetime import datetime
import time
import typing
from functools import reduce

import aiohttp

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    """Manages, and updates the current online players"""
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.dict: dict = {}
        self.all: set[str] = set()
        self.worlds: dict = {}

        self.last_update: datetime = datetime.now()

    def run(self):
        asyncio.create_task(self.update())

    async def update(self):
        t = time.perf_counter()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.wynncraft.com/public_api.php?action=onlinePlayers") as response:
                if not response.ok:
                    return

                players = await response.json()

        del players['request']
        self.dict = players
        self.all = set(sum(players.values(), []))
        self.worlds = reduce(lambda a, b: a | b, map(lambda i: {x: i[0] for x in i[1]}, self.dict.items()))

        # Update playtime
        if playtime := self.bot.tasks.get('PlayerPlaytimeUpdater'):
            playtime.update(self.all)

        await asyncio.sleep(30 - (time.perf_counter() - t))
        self.last_update = datetime.now()

        asyncio.create_task(self.update())

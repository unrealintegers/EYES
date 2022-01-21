from __future__ import annotations

import asyncio
import typing
import time
import aiohttp

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.players = []

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
        self.players = sum(players.values(), [])

        # Update playtime
        if playtime := self.bot.tasks.get('PlayerPlaytimeUpdater'):
            playtime.update(self.players)  # type: ignore

        await asyncio.sleep(30 - (time.perf_counter() - t))
        asyncio.create_task(self.update())

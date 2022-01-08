from __future__ import annotations

import asyncio
import typing

import aiohttp

if typing.TYPE_CHECKING:
    pass


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

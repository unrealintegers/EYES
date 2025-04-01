from __future__ import annotations

import typing
from collections import defaultdict
from datetime import datetime as dt
from datetime import timedelta as td
from itertools import groupby

import aiohttp
from discord.ext import tasks

from ..models import WynncraftAPI

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    """
    Manages, and updates the current online players.
    Also keeps tracks of which players have recently changed worlds
    """

    interval_s = 6

    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.last_update = dt.utcnow()

        self.old_dict: dict[str, str] = {}
        self.dict: dict[str, str] = {}

        self.war_candidates: dict = {}

    @property
    def all(self):
        return self.dict.keys()

    @tasks.loop(seconds=interval_s)
    async def update(self):
        players = await self.fetch_player_list()
        self.update_player_list(players)
        await self.update_playtime(players.keys())

    async def fetch_player_list(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(WynncraftAPI.ONLINE_PLAYERS) as response:
                if not response.ok:
                    self.bot.logger.warn("Failed to fetch Online Players from Wynn API!")
                    return

                players : dict = await response.json()
                players = players['players']

        return players

    def update_player_list(self, players: dict[str, str]):
        players_set = set(players.items())
        # (player, world)
        diff = {t for t in players_set.difference(set(self.old_dict.items())) if t[0] in set(self.old_dict.keys())}
        # (world, guild, player)
        diff = sorted((w, self.bot.guilds_manager.m2g[p], p) for p, w in diff if p in self.bot.guilds_manager.m2g)

        if diff:
            # (world, guild, [player])
            diff = groupby(diff, key=(lambda x: (x[0], x[1])))
            for (w, g), wgps in diff:
                ps = list(zip(*wgps))[2]
                # Always change when there are 2 or more players, or if the last change was more than 10 minutes ago
                if len(ps) > 1 or self.war_candidates.get(g, [dt.min])[0] < dt.now() - td(minutes=10):
                    self.war_candidates[g] = (dt.now(), ps)

        self.old_dict = self.dict
        self.dict = players

    async def update_playtime(self, players: typing.Collection[str]):
        now = dt.utcnow()
        period = now - self.last_update
        value = self.interval_s / 60
        await self.bot.db.copy_to("COPY player_playtime FROM STDIN",
                                  [(p, self.last_update, now, value, period) for p in players])

        guild_playtime = defaultdict(int)
        for player in players:
            guild = self.bot.guilds_manager.m2g.get(player)
            if guild:
                guild_playtime[guild] += value
        await self.bot.db.copy_to("COPY guild_playtime FROM STDIN",
                                  [(g, self.last_update, now, v, period) for g, v in guild_playtime.items()])

        self.last_update = now
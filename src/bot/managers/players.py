from __future__ import annotations

import typing
from datetime import datetime as dt
from datetime import timedelta as td
from itertools import groupby

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    """
    Manages, and updates the current online players.
    Also keeps tracks of which players have recently changed worlds
    """

    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.old_dict: dict[str, str] = {}
        self.dict: dict[str, str] = {}

        self.war_candidates: dict = {}

    def update(self, players: dict[str, str]):
        players_set = set(players.items())
        # (player, world)
        diff = {t for t in players_set.difference(set(self.old_dict.items())) if t[0] in set(self.old_dict.keys())}
        # (world, guild, player)
        diff = sorted((w, self.bot.guilds_manager.m2g[p], p) for p, w in diff if p in self.bot.guilds_manager.m2g)
        print(diff)

        if diff:
            # (world, guild, [player])
            diff = groupby(diff, key=(lambda w, g, p: (w, g)))
            for (w, g), wgps in diff:
                ps = zip(*wgps)[2]
                # Always change when there are 2 or more players, or if the last change was more than 10 minutes ago
                if len(ps) > 1 or self.war_candidates.get(g, [dt.min])[0] < dt.now() - td(minutes=10):
                    self.war_candidates[g] = (dt.now(), ps)

        self.old_dict = self.dict
        self.dict = players

from __future__ import annotations

import typing
from datetime import datetime as dt
from datetime import timedelta as td
from functools import reduce

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    """
    Manages, and updates the current online players.
    Also keeps tracks of which players have recently changed worlds
    """

    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.dict: dict = {}
        self.old_all: set[str] = set()
        self.all: set[str] = set()
        self.worlds: dict = {}

        self.war_candidates: dict = {}

    def update(self, players):
        # world -> [players]
        diff = {w: list(filter(lambda p: p not in self.dict.get(w, []) and (p in self.all or p in self.old_all), p))
                for w, p in players.items()}
        # world -> player -> guild
        diff = {w: {p: self.bot.guilds_manager.m2g[p] for p in ps if p in self.bot.guilds_manager.m2g}
                for w, ps in diff.items() if ps}
        # (world, guild, players)
        diff = [(w, g, set(p for p, g_ in pg.items() if g_ == g))
                for w, pg in diff.items() for g in set(pg.values())]

        if diff:
            for w, g, ps in diff:
                # Always change when there are 2 or more players, or if the last change was more than 10 minutes ago
                if len(ps) > 1 or self.war_candidates.get(g, [dt.min])[0] < dt.now() - td(minutes=10):
                    self.war_candidates[g] = (dt.now(), ps)

        self.dict = players
        self.old_all = self.all
        self.all = set(sum(players.values(), []))
        self.worlds = reduce(lambda a, b: a | b, map(lambda i: {x: i[0] for x in i[1]}, self.dict.items()))

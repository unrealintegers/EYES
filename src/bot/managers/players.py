from __future__ import annotations

import typing
from functools import reduce

if typing.TYPE_CHECKING:
    from ..bot import EYESBot


class PlayerManager:
    """Manages, and updates the current online players"""

    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.dict: dict = {}
        self.all: set[str] = set()
        self.worlds: dict = {}

    def update(self, players):
        self.dict = players
        self.all = set(sum(players.values(), []))
        self.worlds = reduce(lambda a, b: a | b, map(lambda i: {x: i[0] for x in i[1]}, self.dict.items()))

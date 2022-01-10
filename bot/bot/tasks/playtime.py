from typing import List

from ..bot import EYESBot, BotTask
from datetime import datetime as dt


class PlayerPlaytimeUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

    def path(self):
        return self.bot.db.child('wynncraft').child('playtime').child('players')

    def update(self, players: List[str]):
        now = int(dt.utcnow().timestamp())
        update_dict = {f'{k}/{now}/': 0.5 for k in players}
        self.path().update(update_dict)

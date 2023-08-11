from datetime import datetime as dt
import aiocron

from ..bot import EYESBot, BotTask


class PlaytimeUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.interval = 6

    def update(self, players: list[str]):
        now = dt.utcnow()
        value = self.interval / 60
        self.bot.db.run_batch("INSERT INTO player_playtime VALUES (%s, %s, %s)", [(p, now, value) for p in players])

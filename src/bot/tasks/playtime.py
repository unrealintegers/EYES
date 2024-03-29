from datetime import datetime as dt
from datetime import timedelta as td
from typing import List

import aiocron
from pytz import utc
from requests import ConnectionError

from ..bot import EYESBot, BotTask


class PlayerPlaytimeUpdater(BotTask):
    """Updates players' playtime for a short timeframe as raw dicts in database"""
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

    def path(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtimeraw')

    def update(self, players: List[str]):
        now = int(dt.utcnow().timestamp())
        update_dict = {f'{k}/{now}/': True for k in players}
        try:
            self.path().update(update_dict)
        except ConnectionError as e:
            self.bot.logger.error(f"Connection Error while updating: {e}")


class PlayerPlaytimeGrouper(BotTask):
    """
    Groups players' playtime into larger blocks:
      -  1d for older than 30d
      -  1h otherwise
    """

    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.update_short().start()
        self.update_long().start()

    def rawpath(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtimeraw')

    def path(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtime').child('players')

    # Short: Update every 1h
    def update_short(self):
        """Processes raw playtime data to usable playtime data with 1h granularity."""

        @aiocron.crontab("0 * * * *", start=False, tz=utc)
        async def wrapper():
            data = self.rawpath().get().val() or {}
            one_hour_ago = int((dt.utcnow() - td(hours=1)).timestamp())

            # Each entry is 0.5 minutes
            update_dict = {f'{k}/{one_hour_ago}/': 0.5 * len(v) for k, v in data.items()}
            self.path().update(update_dict)
            self.rawpath().remove()

        return wrapper

    # Long: Update every 1d
    def update_long(self):
        @aiocron.crontab("0 0 * * *", start=False, tz=utc)
        async def wrapper():
            pass

        return wrapper

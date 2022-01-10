from datetime import datetime as dt
from datetime import timedelta as td
from typing import List

import aiocron
from pytz import utc

from ..bot import EYESBot, BotTask


class PlayerPlaytimeUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

    def path(self):
        return self.bot.db.child('wynncraft').child('playtimeraw')

    def update(self, players: List[str]):
        now = int(dt.utcnow().timestamp())
        update_dict = {f'{k}/{now}/': True for k in players}
        self.path().update(update_dict)


class PlayerPlaytimeGrouper(BotTask):
    """
    Groups players' playtime into larger blocks:
      -  1d for older than 30d
      -  1h otherwise
    """

    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.update_short.start()
        self.update_long.start()

    def rawpath(self):
        return self.bot.db.child('wynncraft').child('playtimeraw')

    def path(self):
        return self.bot.db.child('wynncraft').child('playtime').child('players')

    # Short: Update every 1h
    @aiocron.crontab("0 * * * *", start=False, tz=utc)
    async def update_short(self):
        """Processes raw playtime data to usable playtime data with 1h granularity."""
        data = self.rawpath().get().val()
        one_hour_ago = int((dt.utcnow() - td(hours=1)).timestamp())

        # Each entry is 0.5 minutes
        update_dict = {f'{k}/{one_hour_ago}/': 0.5 * len(v) for k, v in data.values()}
        self.path().update(update_dict)
        self.rawpath().remove()

    # Long: Update every 1d
    @aiocron.crontab("0 0 * * *", start=False, tz=utc)
    async def update_long(self):
        pass

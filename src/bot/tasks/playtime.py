from collections import defaultdict
from datetime import datetime as dt

from ..bot import EYESBot, BotTask


class PlaytimeUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.interval = 6
        self.last_update = dt.utcnow()

    async def update(self, players: list[str]):
        now = dt.utcnow()
        period = now - self.last_update
        value = self.interval / 60
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

from datetime import datetime as dt

from collections import defaultdict
from ..bot import EYESBot, BotTask


class PlaytimeUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.interval = 6

    def update(self, players: list[str]):
        now = dt.utcnow()
        value = self.interval / 60
        self.bot.db.run_batch("INSERT INTO player_playtime VALUES (%s, %s, %s)", [(p, now, value) for p in players])

        guild_playtime = defaultdict(int)
        for player in players:
            guild = self.bot.guilds_manager.m2g.get(player)
            if guild:
                guild_playtime[guild] += value
        self.bot.db.run_batch("INSERT INTO guild_playtime VALUES (%s, %s, %s)",
                              [(g, now, v) for g, v in guild_playtime.items()])

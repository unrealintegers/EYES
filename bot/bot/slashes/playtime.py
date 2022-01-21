from datetime import datetime as dt
from typing import List

from discord import ApplicationContext, Option

from ..bot import EYESBot, SlashCommand


class PlaytimeCommand(SlashCommand, name="playtime"):
    def __init__(self, bot: EYESBot, guild_ids: List[int]):
        super().__init__(bot, guild_ids)

        self.register(self.playtime)

    def playerpath(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtime').child('players')

    async def playtime(self, ctx: ApplicationContext,
                       player: Option(str, "whose playtime to view"),
                       days: Option(int, "how many days of playtime")):
        """Shows a player's playtime"""
        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        # We default to empty dict as otherwise it might be an empty list
        online_times = self.playerpath().child(player)\
            .order_by_key().start_at(str(prev)).end_at(str(now)).get().val() or {}
        pt = int(sum(online_times.values()))
        await ctx.respond(f"`{player}`'s `{days}d` playtime: `{pt // 60}h{pt % 60}m`")

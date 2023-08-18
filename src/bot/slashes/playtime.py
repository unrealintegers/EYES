from datetime import datetime as dt
from datetime import timedelta as td

import discord.app_commands as slash
from discord import Interaction

from ..bot import EYESBot, SlashCommand


class PlaytimeCommand(SlashCommand, name="playtime"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    @slash.describe(player="whose playtime to view",
                    days="how many days of playtime")
    async def callback(self, ictx: Interaction, player: str, days: int):
        """Shows a player's playtime"""
        now = dt.utcnow()
        prev = now - td(days=days)

        pt = await self.bot.db.fetch_tup("""
            SELECT sum((CASE WHEN start_time >= %s THEN 1
                             ELSE extract(epoch from end_time - %s) / extract(epoch from end_time - start_time)
                             END) * value) AS playtime
            FROM player_playtime WHERE player = %s AND end_time >= %s
        """, (prev, prev, player, prev))
        pt = int(pt[0][0] or 0)
        await ictx.response.send_message(f"`{player}`'s `{days}d` playtime: `{pt // 60}h{pt % 60}m`")

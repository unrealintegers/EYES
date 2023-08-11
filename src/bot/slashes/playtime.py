from datetime import datetime as dt

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
        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        pt = self.bot.db.fetch_tup("""
            SELECT sum((CASE WHEN start_time >= %s THEN 1
                             ELSE extract(epoch from end_time - %s) / extract(epoch from end_time - start_time)
                             END) * value) AS playtime
            FROM player_playtime WHERE player = %s AND end_time >= %s
        """, (prev, prev, player, prev))[0] or 0
        await ictx.response.send_message(f"`{player}`'s `{days}d` playtime: `{pt // 60}h{pt % 60}m`")

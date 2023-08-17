from datetime import datetime as dt

import discord.app_commands as slash
from discord import Interaction

from ..bot import EYESBot, SlashCommand
from ..utils.paginator import ButtonPaginator


class GuildsPlaytimeCommand(SlashCommand, name="guildsplaytime"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    @slash.describe(days="how many days of playtime")
    async def callback(self, ictx: Interaction, days: int):
        """Shows a list of all guilds, ranked by total playtime"""

        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        guild_playtime = await self.bot.db.fetch_tup("""
            SELECT sum((CASE WHEN start_time >= %s THEN 1 
                             ELSE extract(epoch from end_time - %s) / extract(epoch from end_time - start_time) 
                             END) * value) AS playtime 
            FROM guild_playtime WHERE end_time >= %s
            GROUP BY guild ORDER BY playtime
        """, (prev, prev, prev))

        guilds, pts = zip(*guild_playtime)
        avg_online = [round(pt / days / 60 / 24, 3) for pt in pts]
        data = {"Guild": guilds, "Playtime": pts, "Average Online": avg_online}

        paginator = ButtonPaginator(ictx, "Total Playtime of Guilds", data, text='')

        await paginator.generate_embed().respond()

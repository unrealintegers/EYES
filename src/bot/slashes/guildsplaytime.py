from collections import defaultdict

from datetime import datetime as dt

from discord import Interaction
import discord.app_commands as slash

from ..bot import EYESBot, SlashCommand
from ..utils.paginator import ButtonPaginator


class GuildsPlaytimeCommand(SlashCommand, name="guildsplaytime"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    def guildspath(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtime').child('guilds')

    @slash.describe(days="how many days of playtime")
    async def callback(self, ictx: Interaction, days: int):
        """Shows a list of all guilds, ranked by total playtime"""

        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        online_times = self.guildspath().order_by_key().start_at(str(prev)).end_at(str(now)).get().val() or {}
        # Use defaultdict to sum together
        guilds_playtimes = defaultdict(int)
        for d in online_times.values():
            for k, v in d.items():
                guilds_playtimes[k] += round(v)

        guilds, pts = zip(*sorted(guilds_playtimes.items(), key=lambda x: (-x[1], x[0])))
        avg_online = [round(pt / days / 60 / 24, 3) for pt in pts]
        data = {"Guild": guilds, "Playtime": pts, "Average Online": avg_online}

        paginator = ButtonPaginator(ictx, "Total Playtime of Guilds", data, text='')

        await paginator.generate_embed().respond()

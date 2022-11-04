from datetime import datetime as dt

from discord import Interaction
import discord.app_commands as slash

from ..bot import EYESBot, SlashCommand


class PlaytimeCommand(SlashCommand, name="playtime"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    def playerpath(self):
        self.bot.db.path = None
        return self.bot.db.child('wynncraft').child('playtime').child('players')

    @slash.describe(player="whose playtime to view",
                    days="how many days of playtime")
    async def callback(self, ictx: Interaction, player: str, days: int):
        """Shows a player's playtime"""
        now = int(dt.utcnow().timestamp())
        prev = now - days * 86400

        # We default to empty dict as otherwise it might be an empty list
        online_times = self.playerpath().child(player) \
                           .order_by_key().start_at(str(prev)).end_at(str(now)).get().val() or {}
        pt = int(sum(online_times.values()))
        await ictx.response.send_message(f"`{player}`'s `{days}d` playtime: `{pt // 60}h{pt % 60}m`")

from collections import defaultdict
from datetime import datetime as dt
from datetime import timedelta as td

import aiocron
import aiohttp

from ..bot import BotTask, EYESBot
from ..managers import ConfigManager
from ..models import WynncraftAPI


class WarTracker(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.last_territories = None
        self.territory_counts = defaultdict(int)

        self.broadcast_channels = []

        self.update_wars = aiocron.crontab('* * * * * */10', func=self._update_wars, start=False)

    async def init(self):
        await self.update_channels()

        self.update_wars.start()

    async def update_channels(self):
        channels_data = ConfigManager.get_static('warchannels')
        self.broadcast_channels = []
        for g_id, v in channels_data.items():
            if g_id.isdecimal():
                g_id = int(g_id)
            else:
                self.bot.logger.info(f"Invalid Guild ID Format {g_id} for war channels.")
                continue
            for ch_id, gu_dict in v.items():
                gu_name = gu_dict.get('guild', '____')
                terr_filter = list(gu_dict.get('territories', {}).keys()) or []
                claim_filter = list(gu_dict.get('claim', {}).keys()) or []
                claim_filter = sum((self.bot.map_manager.claim_guilds.get(g, []) for g in claim_filter), [])
                final_terr_filter = terr_filter or claim_filter
                if ch_id.isdecimal():
                    ch_id = int(ch_id)
                else:
                    self.bot.logger.info(f"Invalid Channel ID Format {ch_id} for war channels.")
                if g := self.bot.get_guild(g_id):
                    if ch := g.get_channel(ch_id):
                        self.broadcast_channels.append((ch, gu_name, final_terr_filter))
                    else:
                        self.bot.logger.info(f"Channel {ch_id} not found for war channels.")
                else:
                    self.bot.logger.info(f"Guild {g_id} not found for war channels.")

    async def get_territories(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(WynncraftAPI.TERRITORIES) as response:
                if not response.ok:
                    self.bot.logger.error("Failed to fetch Territories from Wynn API!")
                    return None

                territories = await response.json()
                territories = territories.get('territories', {})

        return {t: (d['guild'], dt.strptime(d['acquired'], "%Y-%m-%d %H:%M:%S")) for t, d in territories.items()}

    def generate_string(self, g_from, g_to, prefix_from, prefix_to, territory, players):
        template = "```ansi\n{}[{{}}m{}[0m[{}] -> [{{}}m{}[0m[{}]{} | [{{}}{}m{} [{}]\n```"
        color_terr = self.get_territory_color(territory)

        self.territory_counts[g_from] -= 1
        count_from = self.territory_counts[g_from]
        self.territory_counts[g_to] += 1
        count_to = self.territory_counts[g_to]

        lpad = ' ' * (8 - len(prefix_from) - len(str(count_from)))
        rpad = ' ' * (8 - len(prefix_to) - len(str(count_to)))

        players = ', '.join(players)

        return template.format(lpad, prefix_from, count_from, prefix_to, count_to, rpad, color_terr, territory, players)

    def get_guild_fmt(self, guild, prefix_home):
        style = '1;4;' if guild == prefix_home else ''
        color = '32' if self.bot.map_manager.is_map_guild(guild) else '31'
        return style + color

    def get_territory_color(self, territory):
        return '37' if self.bot.map_manager.owns("NONE", territory) else \
            '33' if self.bot.map_manager.is_ffa(territory) else '34'

    def get_territory_style(self, territory, prefix_home):
        return '1;' if self.bot.map_manager.owns(prefix_home, territory) else ''

    def format_generated_string(self, format_string, territory, prefix_from, prefix_to, prefix_home):
        fmt_from = self.get_guild_fmt(prefix_from, prefix_home)
        fmt_to = self.get_guild_fmt(prefix_to, prefix_home)
        style_terr = self.get_territory_style(territory, prefix_home)
        return format_string.format(fmt_from, fmt_to, style_terr)

    async def _update_wars(self):
        if not self.last_territories:
            self.last_territories = await self.get_territories()
            return

        territories = await self.get_territories()

        territories = {k: (terr, t) if self.last_territories[k][1] < territories[k][1] else self.last_territories[k]
                       for k, (terr, t) in territories.items()}
        transfers = {k: (self.last_territories[k][0], territories[k][0]) for k in self.last_territories
                     if self.last_territories[k][0] != territories[k][0]
                     and self.last_territories[k][1] < territories[k][1]}
        self.territory_counts = defaultdict(int)
        for _, (g, _) in self.last_territories.items():
            self.territory_counts[g] += 1

        for terr, (g_from, g_to) in transfers.items():
            war_id = await self.bot.db.fetch_tup(
                "INSERT INTO territory_capture (time, territory, guild_from, guild_to) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (dt.now(), terr, g_from, g_to)
            )
            war_id = war_id[0][0]

            war_guess = self.bot.players_manager.war_candidates.get(g_to, (dt.min, []))
            if dt.now() - war_guess[0] < td(minutes=10):
                await self.bot.db.copy_to("COPY war_player FROM STDIN", [(war_id, p) for p in war_guess[1]])
                del self.bot.players_manager.war_candidates[g_to]
            else:
                self.bot.logger.warn("War not found for guild %s", g_to)

            prefix_from = self.bot.prefixes_manager.g2p.get(g_from) or '????'
            prefix_to = self.bot.prefixes_manager.g2p.get(g_to) or '????'
            terr_template = self.generate_string(g_from, g_to, prefix_from, prefix_to, terr, war_guess[1])
            for channel, g_home, terr_filter in self.broadcast_channels:
                if terr_filter != [] and terr not in terr_filter:
                    continue

                msg_content = self.format_generated_string(terr_template, terr, prefix_from, prefix_to, g_home)
                await channel.send(msg_content)

        self.last_territories = territories

import asyncio
from collections import defaultdict
import time
from datetime import datetime

import requests

from ..bot import BotTask, EYESBot
from ..models import WynncraftAPI


class WarTracker(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.last_territories = self.get_territories()
        # self.last_update: datetime = datetime.now()
        self.territory_counts = defaultdict(int)

        self.broadcast_channels = []

    async def update_channels(self):
        channels_data = self.bot.db.child("config").child("warchannels").get().val()
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

    @classmethod
    def get_territories(cls):
        resp = requests.get(WynncraftAPI.TERRITORIES)
        if not resp.ok:
            return None

        territories = resp.json()['territories']
        return {t: (d['guild'], d['acquired']) for t, d in territories.items()}

    def generate_string(self, g_from, g_to, prefix_from, prefix_to, territory):
        template = "```ansi\n{}[{{}}m{}[0m[{}] -> [{{}}m{}[0m[{}]{} | [{{}}{}m{}\n```"
        color_terr = self.get_territory_color(territory)

        self.territory_counts[g_from] -= 1
        count_from = self.territory_counts[g_from]
        self.territory_counts[g_to] += 1
        count_to = self.territory_counts[g_to]

        lpad = ' ' * (8 - len(prefix_from) - len(str(count_from)))
        rpad = ' ' * (8 - len(prefix_to) - len(str(count_to)))

        return template.format(lpad, prefix_from, count_from, prefix_to, count_to, rpad, color_terr, territory)

    def get_guild_fmt(self, guild, prefix_home):
        style = '1;4;' if guild == prefix_home else ''
        # print(guild)
        # print(self.bot.map_manager.claim_guilds.keys() )
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

    async def update_wars(self):
        t = time.perf_counter()

        try:
            territories = self.get_territories()
        except requests.exceptions.ConnectionError:
            await asyncio.sleep(10 - (time.perf_counter() - t))
            asyncio.create_task(self.update_wars())
            return

        territories = {k: (terr, t) if self.last_territories[k][1] < territories[k][1] else self.last_territories[k]
                       for k, (terr, t) in territories.items()}
        transfers = {k: (self.last_territories[k][0], territories[k][0]) for k in self.last_territories
                     if self.last_territories[k][0] != territories[k][0]
                     and self.last_territories[k][1] < territories[k][1]}
        self.territory_counts = defaultdict(int)
        for _, g in self.last_territories.items():
            self.territory_counts[g] += 1

        for terr, (g_from, g_to) in transfers.items():
            prefix_from = self.bot.prefixes_manager.g2p.get(g_from, '????')
            prefix_to = self.bot.prefixes_manager.g2p.get(g_to, '????')
            terr_template = self.generate_string(g_from, g_to, prefix_from, prefix_to, terr)
            for channel, g_home, terr_filter in self.broadcast_channels:
                if terr not in terr_filter:
                    continue

                msg_content = self.format_generated_string(terr_template, terr, prefix_from, prefix_to, g_home)
                await channel.send(msg_content)

        await asyncio.sleep(10 - (time.perf_counter() - t))
        # self.last_update = datetime.now()
        self.last_territories = territories

        asyncio.create_task(self.update_wars())

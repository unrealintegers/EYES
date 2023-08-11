import random
import time

import aiohttp
import discord.app_commands as slash
from discord import Interaction

from ..bot import EYESBot, SlashCommand
from ..utils.paginator import ButtonPaginator


class SoulPointCommand(SlashCommand, name="sp"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    @slash.describe(offset="offset for soul point regen in seconds")
    async def callback(self, ictx: Interaction,
                       offset: int = 60):
        """Shows a list of worlds, sorted by closest to next soul point regen tick"""
        await ictx.response.defer()

        async with aiohttp.ClientSession() as session:
            async with session.get("https://athena.wynntils.com/cache/get/serverList") as res:
                if not res.ok:
                    return await ictx.response.send_message("Fetching from SP API failed!", ephemeral=True)
                data = await res.json()

        now = time.time_ns() // (10 ** 9)
        s_20min = 20 * 60
        worlds = sorted(((k, (v['firstSeen'] // (10 ** 3) - now - offset) % s_20min)
                         for k, v in data['servers'].items()), key=lambda x: (x[1], x[0]))

        worlds, times = zip(*worlds)
        data = {"World": worlds, "Time": [f"{t // 60}m{t % 60}s" for t in map(lambda t: t + offset, times)]}
        paginator = ButtonPaginator(ictx, f"Soul Point Regen", data, colour=random.getrandbits(24), text='')
        await paginator.generate_embed().respond()

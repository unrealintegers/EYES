import aiocron
import aiohttp

from ..bot import EYESBot, BotTask
from ..models import WynncraftAPI


class PlayerListUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.update = aiocron.crontab('* * * * * */6', func=self._update, start=False)

    async def init(self):
        self.update.start()

    async def _update(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(WynncraftAPI.ONLINE_PLAYERS) as response:
                if not response.ok:
                    return

                players = await response.json()

        del players['request']

        # Update player list
        self.bot.players_manager.update(players)

        # Update playtime
        if playtime := self.bot.tasks.get('PlaytimeUpdater'):
            await playtime.update(set(sum(players.values(), [])))


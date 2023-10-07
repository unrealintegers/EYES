import aiocron
import aiohttp

from ..bot import EYESBot, BotTask
from ..models import WynncraftAPI


class PlayerListUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

    async def init(self):
        self.update().start()

    def update(self):
        @aiocron.crontab('* * * * * */6', start=False)
        async def callback():
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

        return callback

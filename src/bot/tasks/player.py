import aiocron
import aiohttp

from ..bot import EYESBot, BotTask


class PlayerListUpdater(BotTask):
    def __init__(self, bot: EYESBot):
        super().__init__(bot)

        self.update().start()

    def update(self):
        @aiocron.crontab('* * * * * */30', start=False)
        async def callback():
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.wynncraft.com/public_api.php?action=onlinePlayers") as response:
                    if not response.ok:
                        return

                    players = await response.json()

            del players['request']

            # Update player list
            self.bot.players_manager.update(players)

            # Update playtime
            if playtime := self.bot.tasks.get('PlayerPlaytimeUpdater'):
                playtime.update(set(sum(players.values(), [])))

        return callback

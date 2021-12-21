import aiocron
from pytz import utc


class Cron:
    def __init__(self, bot):
        self.bot = bot
        self.channels = bot.db.fetch("SELECT * FROM cron_channels")

        self.lunch().start()
        self.mail().start()
        self.night().start()
        self.before_reset().start()

    def lunch(self):
        @aiocron.crontab("0 2 * * *", start=False, tz=utc)
        async def wrapper():
            for row in self.channels:
                channel = self.bot.bot.get_channel(row.channel_id)
                await channel.send(f"{row.mention} Lunch Arena has started! "
                                   f"Also don't forget to check your "
                                   f"mail for 50 stamina!")

        return wrapper

    def mail(self):
        @aiocron.crontab("0 9 * * *", start=False, tz=utc)
        async def wrapper():
            for row in self.channels:
                channel = self.bot.bot.get_channel(row.channel_id)
                await channel.send(f"{row.mention} Mail has arrived! "
                                   f"Claim your free gems and stamina!")

        return wrapper

    def night(self):
        @aiocron.crontab("0 11 * * *", start=False, tz=utc)
        async def wrapper():
            for row in self.channels:
                channel = self.bot.bot.get_channel(row.channel_id)
                await channel.send(f"{row.mention} Night Arena has started!")

        return wrapper

    def before_reset(self):
        @aiocron.crontab("50 13 * * *", start=False, tz=utc)
        async def wrapper():
            for row in self.channels:
                channel = self.bot.bot.get_channel(row.channel_id)
                await channel.send(f"{row.mention} 10 minutes before reset! "
                                   f"Check that you have done your raid and "
                                   f"daily quests!")

        return wrapper

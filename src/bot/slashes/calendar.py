import asyncio
from datetime import datetime as dt
from datetime import timedelta
from datetime import timedelta as td

import aiocron
import discord.app_commands as slash
from dateparser import parse as parsedate
from discord import Interaction

from ..bot import EYESBot, SlashCommand


class Reminder:
    def __init__(self, *,
                 discord_id: int,
                 message: str,
                 link: str,
                 timestamp: dt,
                 repeats: int,
                 repeat_interval: td):
        self.discord_id = discord_id
        self.message = message
        self.link = link
        self.timestamp = timestamp
        self.repeats = repeats
        self.repeat_interval = repeat_interval

        self.done = False

    def reminder_str(self):
        remind_str = f"<@{self.discord_id}> **Reminder:** {self.message}\n" \
                     f"Context: {self.link}"

        if not self.done and self.repeats >= 0:
            remind_str += f"Repeats Remaining: {self.repeats}\n"
        if not self.done:
            remind_str += f"Next Reminder: <t:{int(self.timestamp.timestamp())}>"

        return remind_str

    @classmethod
    def from_data(cls, obj: dict) -> 'Reminder':
        if obj['timestamp']:
            obj['timestamp'] = dt.utcfromtimestamp(obj['timestamp'])
        if obj['repeat_interval']:
            obj['repeat_interval'] = td(seconds=obj['repeat_interval'])
        return Reminder(**obj)

    def to_data(self) -> dict:
        if self.done:
            return {}

        self.timestamp = self.timestamp.timestamp()
        self.repeat_interval = self.repeat_interval.total_seconds()
        data = vars(self)
        del data['done']
        return data

    def next(self) -> None:
        if self.repeats == 0:
            self.done = True
            return

        self.timestamp = self.timestamp + self.repeat_interval

        if self.repeats > 0:
            self.repeats -= 1


class RemindCommand(SlashCommand, name="remind"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.DATE_FORMAT = r"%d/%m/%Y %H:%M:%S"

        self.update = aiocron.crontab("0 * * * *", func=self._update, start=False)

        self.update.call_func()
        self.update.start()

    def path(self):
        self.bot.db.path = None
        return self.bot.db.child('utils').child('reminders')

    async def remind(self, reminder_id: str, time: timedelta):
        async def _coro():
            await asyncio.sleep(time.total_seconds())

            if not (data := self.path().child(reminder_id).get().val()):
                return

            reminder = Reminder.from_data(data)

            # We try and calculate the next reminder
            reminder.next()

            await self.bot.get_user(reminder.discord_id).send(reminder.reminder_str())
            self.path().child(reminder_id).set(reminder.to_data())

        asyncio.create_task(_coro())

    @slash.describe(time="time of reminder (can be duration)",
                    message="message",
                    repeats="-1 for infinity, defaults to 0",
                    interval="repeat interval, defaults to reminder time")
    async def callback(
            self, ictx: Interaction,
            time: str, message: str = "something", repeats: int = 0, interval: str = None
    ):
        """Reminds you about something"""
        repeat = (repeats != 0)

        if repeat < -1:
            await ictx.response.send_message("Repeat has to be -1, 0 or a positive integer!", ephemeral=True)

        remind_time = parsedate('in ' + time)

        if remind_time is None:
            await ictx.response.send_message(f"`{time}` is not a valid time.\n"
                                             f"Example: `3h`, `08:05:00`, `07/09/2021 3pm`", ephemeral=True)
            return

        delta = remind_time - dt.now()
        if delta < timedelta(0):
            await ictx.response.send_message("You can't make a reminder to the past!", ephemeral=True)
            return

        if len(message) > 199:
            await ictx.response.send_message("Message length must not exceed 200 characters!", ephemeral=True)
            return

        await ictx.response.defer()

        if interval:
            interval = parsedate("in " + interval) - dt.now()
        else:
            interval = delta

        if repeat and interval < timedelta(hours=1, minutes=59):  # fp error
            await ictx.followup.send("Repeat interval has to be longer than 2h!", ephemeral=True)
            return

        reminder = Reminder(discord_id=ictx.user.id,
                            timestamp=remind_time,
                            message=message,
                            link='',
                            repeats=repeats,
                            repeat_interval=interval)
        reminder_id = self.path().push(reminder.to_data())['name']

        # This does cause some potential overlap, but overlaps will happen
        # with bot restarts/reconnects
        if delta < timedelta(hours=1):
            await self.remind(reminder_id, delta)

        response = await ictx.followup.send(
            f"Your reminder for **{message}** has been set for "
            f"<t:{int(remind_time.timestamp())}>."
        )

        self.path().child(reminder_id).child('link').set(response.jump_url)

    async def _update(self):
        after_1h = dt.utcnow() + td(hours=1)

        if not self.path().get().key():
            return

        reminders = self.path().order_by_child('timestamp').end_at(after_1h.timestamp()).get().each()

        for reminder in reminders:
            time = dt.fromtimestamp(reminder.val()['timestamp']) - dt.utcnow()
            await self.remind(reminder.key(), time)

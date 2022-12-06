import json

from discord import Interaction
import discord.app_commands as slash

from datetime import datetime as dt
import pytz

from ..bot import EYESBot, SlashGroup
from ..models import choice


class ConfigCommand(SlashGroup, name="config"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.command(name="set")(self.set_)
        self.command(name="timezone")(self.set_timezone)

    @slash.describe(path="config path, use / for separator",
                    value="JSON value to set",
                    scope="where this should be applied")
    @slash.choices(scope=[choice("user"), choice("guild"), choice("global")])
    async def set_(self, ictx: Interaction, path: str, value: str, scope: str):
        """Sets a config flag"""
        if scope == "global":
            client = ictx.client
            if not isinstance(client, EYESBot):
                return
            if not await client.is_owner(ictx.user):
                await ictx.response.send_message("Insufficient permissions for scope: `global`.", ephemeral=True)
                return
        if scope == "guild":
            if not ictx.guild:
                await ictx.response.send_message("Must be used in a guild.", ephemeral=True)
                return
            elif ictx.user.guild_permissions.manage_guild:
                await ictx.response.send_message("You need the `Manage Server` permission to use scope: `guild`.")
                return

        # Clean the path
        path = path.lower().strip().split('/')
        # Validate the path
        allowed_paths = self.bot.db.child("paths").get().val().values()
        if path[0] not in allowed_paths:
            await ictx.response.send_message("Invalid Path!", ephemeral=True)
            return

        # Child to the path
        db_path = self.bot.db.child("config").child(scope)
        if scope == "user":
            db_path = db_path.child(ictx.user.id)
        elif scope == "guild":
            db_path = db_path.child(ictx.guild.id)
        for ext in path:
            db_path = db_path.child(ext)

        db_path.set(json.loads(value))
        await ictx.response.send_message("Done!", ephemeral=True)

    @slash.describe(timezone="your timezone, in IANA format")
    async def set_timezone(self, ictx: Interaction, timezone: str):
        """Sets your timezone in the config."""
        try:
            tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            await ictx.response.send_message(
                "Timezone not found! See [Wikipedia](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) "
                "for a list, or [timezonedb](https://timezonedb.com/) uses your current location to show you your "
                "time zone. (It should look like `US/Eastern` or `Europe/Paris` with a slash)", ephemeral=True
            )
        else:
            self.bot.db.child('config').child('user').child(ictx.user.id).child('tz').set(tz.zone)
            now = dt.now(tz=tz)
            await ictx.response.send_message(
                f"Successfully set your timezone to `{tz.zone}`! Your current time is `{now.strftime('%I:%M%p')}`."
                f"If this is incorrect, please run this command again with the correct timezone.\n"
                f"See [Wikipedia](<https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>) "
                "for a list, or [timezonedb](<https://timezonedb.com/>) uses your current location to show you your "
                "time zone. (It should look like `US/Eastern` or `Europe/Paris` with a slash)", ephemeral=True
            )
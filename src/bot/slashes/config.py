import json
import zlib
from datetime import datetime as dt

import discord.app_commands as slash
import pytz
from discord import Interaction

from ..bot import EYESBot, SlashGroup
from ..managers import ConfigManager
from ..models import choice
from ..utils.wynn import parse_map_string


class ConfigCommand(SlashGroup, name="config"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.command(name="set")(self.set_)
        self.command(name="timezone")(self.set_timezone)
        self.command(name="claims")(self.update_map)

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
        allowed_paths = ConfigManager.get_static('paths')
        if path[0] not in allowed_paths:
            await ictx.response.send_message("Invalid Path!", ephemeral=True)
            return

        # Child to the path
        if scope == "user":
            ConfigManager.set_user(ictx.user.id, path, json.loads(value))
        elif scope == "guild":
            ConfigManager.set_guild(ictx.guild.id, path, json.loads(value))

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
            ConfigManager.set_user(ictx.user.id, 'tz', tz.zone)
            now = dt.now(tz=tz)
            await ictx.response.send_message(
                f"Successfully set your timezone to `{tz.zone}`! Your current time is `{now.strftime('%I:%M%p')}`."
                f"If this is incorrect, please run this command again with the correct timezone.\n"
                f"See [Wikipedia](<https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>) "
                "for a list, or [timezonedb](<https://timezonedb.com/>) uses your current location to show you your "
                "time zone. (It should look like `US/Eastern` or `Europe/Paris` with a slash)", ephemeral=True
            )

    @slash.describe(map_str="b85 zlib")
    async def update_map(self, ictx: Interaction, map_str: str):
        if ictx.user.id != 330509305663193091:
            await ictx.response.send_message(f"What do you think you are doing?", ephemeral=True)

        try:
            map_dict = parse_map_string(map_str)
        except (zlib.error, TypeError, SyntaxError) as e:
            await ictx.response.send_message(f"Encountered {type(e)} while parsing map string!", ephemeral=True)
            return
        if not isinstance(map_dict, dict):
            await ictx.response.send_message(f"Wrong data type. Expected `dict`, found `{type(map_dict)}.`",
                                             ephemeral=True)
            return

        map_dict = {k: '_' if v is None else v for k, v in map_dict.items()}
        ConfigManager.set_static('claims', map_dict)

        await ictx.response.send_message("Successfully updated the map.", ephemeral=True)

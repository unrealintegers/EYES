import json

from discord import ApplicationContext, Option, OptionChoice

from ..bot import EYESBot, SlashCommand


class ConfigCommand(SlashCommand, name="config"):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.config = self.bot.bot.create_group(
            "config", "No Description", guild_ids=self.guild_ids
        )

        self.config.command(name="set")(self.set_)

    async def set_(self, ctx: ApplicationContext,
                   path: Option(str, "config path, use / for separator"),
                   value: Option(str, "JSON value to set"),
                   scope: Option(str, "where this should be applied",
                                 choices=[OptionChoice("user"),
                                          OptionChoice("guild"),
                                          OptionChoice("global")])):
        """Sets a config flag"""
        if scope == "global":
            if not await ctx.bot.is_owner(ctx.user):
                await ctx.respond("Insufficient permissions for scope: `global`.")
                return
        if scope == "guild":
            if not ctx.guild:
                await ctx.respond("Must be used in a guild.")
                return
            elif ctx.author.guild_permissions.manage_guild:
                await ctx.respond("You need the `Manage Server` permission to use scope: `guild`.")
                return

        # Clean the path
        path = path.lower().strip().split('/')
        # Validate the path
        allowed_paths = self.bot.db.child("paths").get().val().values()
        if path[0] not in allowed_paths:
            await ctx.respond("Invalid Path!")
            return

        # Child to the path
        db_path = self.bot.db.child("config").child(scope)
        for ext in path:
            db_path = db_path.child(ext)

        db_path.set(json.loads(value))
        await ctx.respond("Done!")

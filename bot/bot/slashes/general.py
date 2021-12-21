from collections import defaultdict
from datetime import datetime as dt
from typing import List

from discord import ApplicationContext, Option
from discord import Member

from ..bot import EYESBot, SlashCommand


class Impersonation(SlashCommand, name="impersonate"):
    def __init__(self, bot: EYESBot, guild_ids: List[int]):
        super().__init__(bot, guild_ids)

        self.cooldowns = defaultdict(lambda: [dt.utcnow(), 3])

        self.register(self.impersonate)

    async def impersonate(
            self, ctx: ApplicationContext,
            user: Option(Member, "who to impersonate"),
            message: Option(str, "message")
    ):
        """Speaks on behalf of someone else (Limit: 4/20min)"""
        td = dt.utcnow() - self.cooldowns[user][0]
        self.cooldowns[user][0] = dt.utcnow()
        self.cooldowns[user][1] += td.total_seconds() / 300
        self.cooldowns[user][1] = min(4, self.cooldowns[user][1])

        if self.cooldowns[user][1] < 1 and ctx.user.id != 330509305663193091:
            cd = (1 - self.cooldowns[user][1]) * 300
            await ctx.respond(
                f"This command is on cooldown for another {cd}s.",
                ephemeral=True)
            return

        self.cooldowns[user][1] -= 1

        webhooks = await ctx.channel.webhooks()

        if not webhooks:
            webhook = await ctx.channel.create_webhook(
                name='VegeBot',
            )
        else:
            webhook = webhooks[0]

        await webhook.send(
            content=message,
            username=user.display_name,
            avatar_url=user.avatar.url
        )

        await ctx.respond("Done", ephemeral=True)

from typing import Optional

from collections import defaultdict
from datetime import datetime as dt

from discord import Interaction
from discord import Member, Webhook
from discord.utils import find
import discord.app_commands as slash

from ..bot import EYESBot, SlashCommand


class ImpersonateCommand(SlashCommand, name="impersonate", guild_only=True):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

        self.cooldowns = defaultdict(lambda: [dt.utcnow(), 3])

    @slash.describe(user="who to impersonate", message="message")
    async def callback(
            self, ictx: Interaction,
            user: Member, message: str
    ):
        """Speaks on behalf of someone else (Limit: 4/20min)"""
        td = dt.utcnow() - self.cooldowns[user][0]
        self.cooldowns[user][0] = dt.utcnow()
        self.cooldowns[user][1] += td.total_seconds() / 300
        self.cooldowns[user][1] = min(4, self.cooldowns[user][1])

        if self.cooldowns[user][1] < 1 and ictx.user.id != 330509305663193091:
            cd = (1 - self.cooldowns[user][1]) * 300
            await ictx.response.send_message(f"This command is on cooldown for another {cd}s.", ephemeral=True)
            return

        self.cooldowns[user][1] -= 1

        webhooks = await ictx.channel.webhooks()
        webhook: Optional[Webhook] = find(lambda x: x.token, webhooks)

        if not webhook:
            webhook = await ictx.channel.create_webhook(
                name='EYES',
            )

        await webhook.send(
            content=message,
            username=user.display_name,
            avatar_url=user.avatar.url
        )

        await ictx.response.send_message("Done", ephemeral=True)

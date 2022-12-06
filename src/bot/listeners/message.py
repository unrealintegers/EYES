from typing import TYPE_CHECKING

import time

from discord import Message, Status
from discord.utils import MISSING
from discord import utils

if TYPE_CHECKING:
    from ..bot import EYESBot


class MessageListener:
    """A message listener, currently used to listen for messages containing pings."""
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.bot.add_listener(self.on_message)

        # Role -> List of Members
        self.replacements = {}
        self.last_update = time.time()

    async def update_replacements(self):
        """Updates the replacements dict with guilds,
           mapping each starting role to a list of members with the replaced role."""
        def insert_members(roles, replacement_dict):
            if 'role' in replacement_dict:
                replacement_dict['members'] = utils.get(roles, id=int(replacement_dict['role'])).members
            else:
                replacement_dict['members'] = []

            return replacement_dict

        replacements = self.bot.db.child('config').child('onlinepings').child('guild').get().val()
        for guild_id in replacements:
            guild = self.bot.get_guild(int(guild_id))
            if guild is None:
                continue

            roles = await guild.fetch_roles()
            self.replacements[int(guild_id)] = {utils.get(roles, id=int(k)): insert_members(roles, v)
                                                for k, v in replacements[guild_id].items()}

    async def on_message(self, message: Message):
        # a lazy check before we start replacing
        if message.role_mentions:
            await self.ping_online_only(message)

        # Update replacements if 60 seconds have passed
        if time.time() - self.last_update > 60:
            await self.update_replacements()
            self.last_update = time.time()

    async def ping_online_only(self, message: Message):
        """
        Replaces pings in certain messages with online-only pings.
        The bot will send a webhook message pinging the online members.
        """

        replacements = self.replacements.get(message.guild.id, {})
        eligible_replacements = {k for k, v in replacements.items() if self.eligible_replacement(message, v)}
        included_roles = list(filter(lambda r: r in eligible_replacements, message.role_mentions))
        eligible_members = sum(map(lambda r: replacements.get(r, {}).get('members', []), included_roles), [])
        online_members = set(filter(lambda m: m.status is Status.online, eligible_members))

        if not online_members:
            return

        ping = " ".join(map(lambda m: m.mention, online_members))

        # Tries to find the existing webhook otherwise creates one
        webhooks = await message.channel.webhooks()
        webhook = utils.find(lambda w: w.token is not None, webhooks)
        if webhook is None:
            webhook = await message.channel.create_webhook(name="EYES")

        avatar = message.author.avatar.url if message.author.avatar is not None else MISSING
        ping_msg = await webhook.send(ping, username=message.author.display_name, avatar_url=avatar, wait=True)
        if ping_msg is not None:
            await ping_msg.delete()

    def eligible_replacement(self, message: Message, replacement: dict):
        allowed_channels = replacement.get('allowed_channels', [])
        disallowed_channels = replacement.get('disallowed_channels', [])
        allowed_roles = replacement.get('allowed_roles', [])
        disallowed_roles = replacement.get('disallowed_roles', [])

        if allowed_channels and message.channel.id not in allowed_channels:
            return False
        if disallowed_channels and message.channel.id in disallowed_channels:
            return False
        if allowed_roles and not any(str(r.id) in allowed_roles for r in message.author.roles):
            return False
        if disallowed_roles and any(str(r.id) in disallowed_roles for r in message.author.roles):
            return False

        return True

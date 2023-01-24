from discord import Message, Interaction

import emoji

from ..bot import EYESBot, ContextMenuCommand


class VoteCommand(ContextMenuCommand, name='Set Up Vote', guild_only=True):
    def __init__(self, bot: EYESBot, guild_ids: list[int]):
        super().__init__(bot, guild_ids)

    async def callback(self, ictx: Interaction, message: Message):
        if 'voting' not in message.channel.name:
            await ictx.response.send_message("Can only be used in voting channels!", ephemeral=True)
            return

        lines = message.content.split('\n')
        lines_emojis = map(emoji.emoji_list, lines)
        valid_emojis = {
            emojis[0]['emoji'] for emojis in lines_emojis
            if len(emojis) == 1
        }
        for emoji_str in valid_emojis:
            await message.add_reaction(emoji_str)

        await ictx.response.send_message(f"Added {len(valid_emojis)} reactions.", ephemeral=True)

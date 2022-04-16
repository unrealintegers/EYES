from discord import Interaction, Member
from discord import Object
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..bot import EYESBot


class ReactionListener:
    def __init__(self, bot: 'EYESBot'):
        self.bot = bot

        self.bot.bot.add_listener(self.on_interaction)

    @staticmethod
    async def role_action(member: Member, role_id: int, required_ids: list[int]):
        if member.get_role(role_id):
            await member.remove_roles(Object(id=role_id))
            return "Role Successfully Removed!"
        else:
            role_ids = [r.id for r in member.roles]
            if all(int(req) in role_ids for req in required_ids):
                await member.add_roles(Object(id=role_id))
                return "Role Successfully Added!"
            else:
                return "Insufficient Permissions!"

    async def on_interaction(self, interaction: Interaction):
        if interaction.guild is None:
            return

        custom_id = getattr(interaction, "custom_id", None)
        if custom_id is None or not custom_id.startswith('$'):
            return

        action, _, arg = custom_id[1:].partition(' ')

        if action == "role":
            role_id, *reqs = arg.split()
            member = interaction.user

            message = await self.role_action(member, int(role_id), reqs)
            await interaction.response.send_message(message, ephemeral=True)


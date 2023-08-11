import re
from typing import Optional

from discord import Message, Embed, Interaction
from discord import TextChannel, Member
from discord import utils
from discord.components import SelectOption
from discord.enums import ButtonStyle, ChannelType, MessageType
from discord.ui import View, Button, Select

from ..bot import EYESBot


class AutoroleWizard:
    def __init__(self, bot: EYESBot):
        self.bot = bot

        self.author: Optional[Member] = None
        self.thread: Optional[TextChannel] = None
        self.creation_msg: Optional[Message] = None

        self.instructions: Optional[Message] = None
        self.original_view: Optional[View] = None

        self.sample: Optional[Message] = None
        self.sample_embed: Optional[Embed] = None
        self.sample_view: Optional[View] = None

    @classmethod
    async def new(cls, bot: EYESBot, author: Member, channel: TextChannel):
        self = AutoroleWizard(bot)
        self.author = author

        await self.init_thread(channel)

        self.sample = await self.thread.send("This is a sample of what users will see...")
        self.sample_embed = None
        self.sample_view = View()

        return self

    @classmethod
    async def from_msg(cls, bot: EYESBot, author: Member, channel: TextChannel, original: Message):
        self = AutoroleWizard(bot)
        self.author = author

        await self.init_thread(channel)

        self.sample_view = View.from_message(original)
        self.sample_embed = (original.embeds or [None])[0]
        self.sample = await self.thread.send(original.content, embed=self.sample_embed, view=self.sample_view)

        return self

    async def init_thread(self, channel: TextChannel):
        thread_type = ChannelType.private_thread if channel.guild.premium_tier >= 2 else ChannelType.public_thread

        self.thread = await channel.create_thread(name="Autorole Wizard", type=thread_type)
        self.creation_msg = await utils.get(channel.history(limit=5), type=MessageType.thread_created)

        embed = Embed(title="Autorole Wizard",
                      description="Below you will find a message which will be a sample of what your autorole prompt "
                                  "will look like. You may edit that using the buttons on this message.",
                      colour=0x395863)

        self.generate_view()

        self.instructions = await self.thread.send(content=self.author.mention, embed=embed, view=self.original_view)

    def generate_view(self):
        # Cancel | Edit Text | Send
        # Embed Actions ?
        # <OPT> Field Actions ?
        # Add Button | Edit Button | Remove Button

        close_btn = Button(label="Close", style=ButtonStyle.danger, row=4)
        close_btn.callback = self.close
        edit_text_btn = Button(label="Edit Text", style=ButtonStyle.secondary, row=4)
        edit_text_btn.callback = self.edit_text
        send_btn = Button(label="Send", style=ButtonStyle.success, row=4)
        send_btn.callback = self.send

        embed_select = Select(placeholder="Embed Actions", options=[
            SelectOption(label="Add Embed", value="add_embed"),
            SelectOption(label="Remove Embed", value="remove_embed"),
            SelectOption(label="Set Title", value="set_title"),
            SelectOption(label="Set Description", value="set_description"),
            SelectOption(label="Set Colour", value="set_colour")
        ], row=0)
        embed_select.callback = self.select_actions

        button_select = Select(placeholder="Button Actions", options=[
            SelectOption(label="Add Button", value="add_button"),
            SelectOption(label="Add Link", value="add_link"),
            SelectOption(label="Remove Button", value="remove_button")
        ], row=2)
        button_select.callback = self.select_actions

        # 30 minute timeout
        self.original_view = View(timeout=1800)
        self.original_view.add_item(embed_select)
        self.original_view.add_item(button_select)
        self.original_view.add_item(close_btn)
        self.original_view.add_item(edit_text_btn)
        self.original_view.add_item(send_btn)

    def message_check(self, msg: Message):
        return msg.channel == self.thread and self.author == msg.author

    async def close(self, _: Interaction):
        await self.thread.delete()
        await self.creation_msg.delete()
        del self

    async def edit_text(self, interaction: Interaction):
        await interaction.response.send_message("Type your desired message below, `_` for blank:")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)
        if msg.content == "_":
            await self.sample.edit(content="")
        else:
            await self.sample.edit(content=msg.content)

        await msg.delete()
        orig = await interaction.original_response()
        await orig.delete()

    async def send(self, interaction: Interaction):
        await interaction.response.send_message("Type a channel to send it to:")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)

        # Fetch the thingy so it is up to date
        self.sample = await self.sample.channel.fetch_message(self.sample.id)

        channel_match = re.fullmatch(r"<#(\d{16,20})>", msg.content) or re.fullmatch(r"(\d{16,20})", msg.content)
        if channel_match is None:
            await interaction.followup.send("Invalid Channel!", ephemeral=True)
        else:
            channel_id = int(channel_match.group(1))
            channel = await interaction.guild.fetch_channel(channel_id)
            await channel.send(content=self.sample.content, embeds=self.sample.embeds, view=self.sample_view)

        await msg.delete()
        orig = await interaction.original_response()
        await orig.delete()

    async def select_actions(self, interaction: Interaction):
        action = interaction.data['values'][0]
        await getattr(self, action)(interaction)
        await self.instructions.edit(view=self.original_view)

    async def add_embed(self, interaction: Interaction):
        await interaction.response.send_message("Adding Embed..")
        if not self.sample_embed:
            self.sample_embed = Embed(description="<Empty Embed>")
            await self.sample.edit(embed=self.sample_embed)
        else:
            await interaction.followup.send("Embed already exists!", ephemeral=True)
        orig = await interaction.original_response()
        await orig.delete()

    async def remove_embed(self, interaction: Interaction):
        await interaction.response.send_message("Removing Embed..")
        if self.sample_embed:
            self.sample_embed = None
            await self.sample.edit(embeds=[])
        else:
            await interaction.followup.send("Embed doesn't exist!", ephemeral=True)
        orig = await interaction.original_response()
        await orig.delete()

    async def set_title(self, interaction: Interaction):
        await interaction.response.send_message("Type your desired title below:")
        if self.sample_embed:
            msg: Message = await self.bot.wait_for("message", check=self.message_check)

            self.sample_embed.title = msg.content
            await self.sample.edit(embed=self.sample_embed)
            await msg.delete()
        else:
            await interaction.followup.send("Embed doesn't exist!", ephemeral=True)
        orig = await interaction.original_response()
        await orig.delete()

    async def set_description(self, interaction: Interaction):
        await interaction.response.send_message("Type your desired description below:")
        if self.sample_embed:
            msg: Message = await self.bot.wait_for("message", check=self.message_check)

            self.sample_embed.description = msg.content
            await self.sample.edit(embed=self.sample_embed)
            await msg.delete()
        else:
            await interaction.followup.send("Embed doesn't exist!", ephemeral=True)
        orig = await interaction.original_response()
        await orig.delete()

    async def set_colour(self, interaction: Interaction):
        await interaction.response.send_message("Type your desired colour hex below: ")
        if self.sample_embed:
            msg: Message = await self.bot.wait_for("message", check=self.message_check)
            try:
                colour = int(msg.content, 16)
            except ValueError:
                await interaction.response.edit("Invalid Colour!")
                return

            if colour < 0 or colour > (1 << 24):
                await interaction.response.edit("Invalid Colour!")
                return

            self.sample_embed.colour = colour
            await self.sample.edit(embed=self.sample_embed)
            await msg.delete()
        else:
            await interaction.followup.send("Embed doesn't exist!", ephemeral=True)
        orig = await interaction.original_response()
        await orig.delete()

    async def add_button(self, interaction: Interaction):
        def button_check(_interaction: Interaction):
            return _interaction.channel_id == self.thread.id and \
                   _interaction.data.get("custom_id") in ["primary", "danger", "success", "secondary"]

        await interaction.response.send_message("Type the desired name of the button: (`_` for blank)")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)
        title = None if msg.content == "_" else msg.content
        await msg.delete()

        orig = await interaction.original_response()

        await orig.edit(content="Type the desired emoji for the button: (`_` for blank)")
        msg = await self.bot.wait_for("message", check=self.message_check)
        emoji = None if msg.content == "_" else msg.content
        await msg.delete()

        if title is None and emoji is None:
            await interaction.followup.send("Name and Emoji cannot both be empty.", ephemeral=True)
            await orig.delete()
            return

        button_options = View()
        button_options.add_item(Button(label="Blurple", style=ButtonStyle.primary, custom_id="primary"))
        button_options.add_item(Button(label="Red", style=ButtonStyle.danger, custom_id="danger"))
        button_options.add_item(Button(label="Green", style=ButtonStyle.success, custom_id="success"))
        button_options.add_item(Button(label="Grey", style=ButtonStyle.secondary, custom_id="secondary"))

        await orig.edit(content="Choose the desired colour for the button:", view=button_options)
        i9n = await self.bot.wait_for("interaction", check=button_check)
        style = getattr(ButtonStyle, i9n.data.get("custom_id"))

        await orig.edit(content="Type the desired action when the button is pressed:\n"
                                "`role <Role ID> <Required IDs>` grants or revokes the role "
                                "to anyone who has the IDs required.", view=None)
        msg = await self.bot.wait_for("message", check=self.message_check)
        action, _, arg = msg.content.partition(' ')

        custom_id = None
        if action == "role":
            role_id, *reqs = arg.split()
            if not role_id.isdecimal():
                await interaction.followup.send("Invalid Role ID!")
                await orig.delete()
                return
            elif not all(req.isdecimal() or req in ('|', '&') for req in reqs):
                await interaction.followup.send("Invalid Required IDs!")
                await orig.delete()
                return
            else:
                custom_id = '$' + msg.content

        button = Button(label=title, emoji=emoji, style=style, custom_id=custom_id)
        self.sample_view.add_item(button)
        await msg.delete()
        await orig.delete()
        await self.sample.edit(view=self.sample_view)

    async def add_link(self, interaction: Interaction):
        await interaction.response.send_message("Type the desired label for the link:")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)
        label = msg.content
        await msg.delete()

        orig = await interaction.original_response()

        await orig.edit(content="Type the desired URL for the link")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)
        url = msg.content
        await msg.delete()

        button = Button(label=label, url=url)
        self.sample_view.add_item(button)
        await orig.delete()
        await self.sample.edit(view=self.sample_view)

    async def remove_button(self, interaction: Interaction):
        await interaction.response.send_message("Type the index or name of the button to remove:")
        msg: Message = await self.bot.wait_for("message", check=self.message_check)
        if msg.content.isdecimal():
            index = int(msg.content)
            if index > len(self.sample_view.children):
                await interaction.followup.send("Index out of range!", ephemeral=True)
            else:
                item = self.sample_view.children[index-1]
                self.sample_view.remove_item(item)
        else:
            item = utils.get(self.sample_view.children, label=msg.content)
            if item is not None:
                self.sample_view.remove_item(item)
            else:
                await interaction.followup.send("Name not found!", ephemeral=True)

        await msg.delete()
        await self.sample.edit(view=self.sample_view)
        orig = await interaction.original_response()
        await orig.delete()

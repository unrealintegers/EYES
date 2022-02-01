from typing import Dict, Optional, Sequence

from discord import Message, Embed, ApplicationContext
from discord.ui import View, Button
from discord.abc import Messageable
from discord.utils import escape_markdown


class TablePaginator:
    def __init__(self,
                 ctx: Messageable,
                 title: str,
                 data: Dict[str, Sequence],
                 perpage: int = 10,
                 **kwargs):

        self.title = title
        self.embed_args = kwargs

        self.data = data
        lengths = {len(v) for k, v in data.items()}
        if len(lengths) != 1:
            raise ValueError("Data items do not have the same length.")

        self.length = next(iter(lengths))
        self.perpage = perpage
        self.ctx = ctx
        self.message: Optional[Message] = None

        self.start = 0
        self.end = perpage
        self.embed = None

    def generate_embed(self):
        embed = Embed(title=self.title, **self.embed_args)

        for k, vs in self.data.items():
            mapped_vs = map(lambda x: escape_markdown(str(x)), vs[self.start:self.end])
            embed.add_field(name=k, value='\n'.join(mapped_vs), inline=True)

        self.embed = embed
        return self

    async def respond(self):
        """Responds by sending a new embed if one doesn't exist, or edits an existing embed."""
        if isinstance(self.ctx, ApplicationContext):
            if not self.ctx.response.is_done():
                return await self.send()
            else:
                return await self.edit()
        else:
            if self.message is None:
                return await self.send()
            else:
                return await self.edit()

    async def send(self):
        """Sends the embed to the provided channel."""
        if self.embed is None:
            raise ValueError("Embed has not been generated yet!")

        if isinstance(self.ctx, ApplicationContext):
            return await self.ctx.send_response(embed=self.embed)
        else:
            self.message = await self.ctx.send(embed=self.embed)
            return self.message

    async def edit(self):
        """Edits an existing embed."""
        if self.embed is None:
            raise ValueError("Embed has not been generated yet!")
        if isinstance(self.ctx, ApplicationContext):
            return await self.ctx.edit(embed=self.embed)
        else:
            if self.message is None:
                raise ValueError("No message exists to edit.")
            await self.message.edit(embed=self.embed)
            return self.message

    def scroll(self, offset):
        # We ensure that each page starts on a multiple of self.perpage
        self.start = min(max(self.start + offset, 0), self.length - 1 - (self.length - 1) % self.perpage)
        self.end = min(self.start + self.perpage, self.length)
        return self

    def first_page(self):
        self.scroll(-self.length)
        return self

    def last_page(self):
        # Round to nearest multiple of perpage
        self.scroll(self.length)
        return self

    def prev_page(self):
        self.scroll(-self.perpage)
        return self

    def next_page(self):
        self.scroll(self.perpage)
        return self


class ButtonPaginator(TablePaginator):
    """A button-based table paginator using buttons for navigation."""
    def __init__(self,
                 ctx: Messageable,
                 title: str,
                 data: Dict[str, Sequence],
                 perpage: int = 10,
                 **kwargs
                 ):
        super().__init__(ctx, title, data, perpage, **kwargs)

        first_page_button = Button(emoji='⏪')
        first_page_button.callback = self.first_page_callback
        last_page_button = Button(emoji='⏩')
        last_page_button.callback = self.last_page_callback
        prev_page_button = Button(emoji='◀')
        prev_page_button.callback = self.prev_page_callback
        next_page_button = Button(emoji='▶')
        next_page_button.callback = self.next_page_callback

        buttons = [
            first_page_button,
            prev_page_button,
            next_page_button,
            last_page_button
        ]

        self.view = View(*buttons)

    async def respond(self):
        """Responds by sending a new embed if one doesn't exist, or edits an existing embed."""
        if isinstance(self.ctx, ApplicationContext):
            if self.ctx.response.is_done():
                return await self.edit()
            else:
                return await self.send()
        else:
            if self.message is None:
                return await self.send()
            else:
                return await self.edit()

    async def send(self):
        """Sends the embed to the provided channel."""
        if self.embed is None:
            raise ValueError("Embed has not been generated yet!")

        if isinstance(self.ctx, ApplicationContext):
            return await self.ctx.send_response(embed=self.embed, view=self.view)
        else:
            self.message = await self.ctx.send(embed=self.embed, view=self.view)
            return self.message

    async def edit(self):
        """Edits an existing embed."""
        if self.embed is None:
            raise ValueError("Embed has not been generated yet!")
        if isinstance(self.ctx, ApplicationContext):
            return await self.ctx.edit(embed=self.embed, view=self.view)
        else:
            if self.message is None:
                raise ValueError("No message exists to edit.")
            await self.message.edit(embed=self.embed, view=self.view)
            return self.message

    async def first_page_callback(self, *_):
        return await self.first_page().generate_embed().respond()

    async def last_page_callback(self, *_):
        return await self.last_page().generate_embed().respond()

    async def prev_page_callback(self, *_):
        return await self.prev_page().generate_embed().respond()

    async def next_page_callback(self, *_):
        return await self.next_page().generate_embed().respond()

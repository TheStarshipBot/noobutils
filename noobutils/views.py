from __future__ import annotations

import discord

from redbot.core import commands

from typing import Dict, Optional, Union, List, Any, TYPE_CHECKING, Union

from .utility import get_button_colour, access_denied

if TYPE_CHECKING:
    from discord import Message, InteractionMessage, WebhookMessage

__all__ = (
    "NoobPaginator",
    "NoobConfirmation"
)
class NoobPaginator(discord.ui.View):
    """
    originally from pranoy but i modified to work for red discord bot

    https://github.com/PranoyMajumdar/dispie/blob/main/dispie/paginator/__init__.py
    """
    message: Optional[Message] = None

    def __init__(
        self,
        pages: List[Any],
        *,
        timeout: Optional[float] = 180.0,
        delete_message_after: bool = False,
        per_page: int = 1,
    ):
        super().__init__(timeout=timeout)
        self.delete_message_after: bool = delete_message_after
        self.current_page: int = 0

        self.context: Optional[commands.Context] = None
        self.interaction: Optional[discord.Interaction] = None
        self.per_page: int = per_page
        self.pages: Any = pages
        total_pages, left_over = divmod(len(self.pages), self.per_page)
        if left_over:
            total_pages += 1

        self.max_pages: int = total_pages
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1

    def stop(self) -> None:
        self.message = None
        self.context = None
        self.interaction = None

        super().stop()

    def get_page(self, page_number: int) -> Any:
        if page_number < 0 or page_number >= self.max_pages:
            self.current_page = 0
            return self.pages[self.current_page]

        if self.per_page == 1:
            return self.pages[page_number]
        base = page_number * self.per_page
        return self.pages[base: base + self.per_page]

    def format_page(self, page: Any) -> Any:
        return page

    async def get_page_kwargs(self, page: Any) -> Dict[str, Any]:
        formatted_page = await discord.utils.maybe_coroutine(self.format_page, page)

        kwargs = {"content": None, "embeds": [], "view": self}
        if isinstance(formatted_page, str):
            kwargs["content"] = formatted_page
        elif isinstance(formatted_page, discord.Embed):
            kwargs["embeds"] = [formatted_page]
        elif isinstance(formatted_page, list):
            if not all(isinstance(embed, discord.Embed) for embed in formatted_page):
                raise TypeError(
                    "All elements in the list must be of type Embed")

            kwargs["embeds"] = formatted_page
        elif isinstance(formatted_page, dict):
            return formatted_page

        return kwargs

    async def update_page(self, interaction: discord.Interaction) -> None:
        if self.message is None:
            self.message = interaction.message

        kwargs = await self.get_page_kwargs(self.get_page(self.current_page))
        self.first_page.disabled = self.current_page <= 0
        self.previous_page.disabled = self.current_page <= 0
        self.next_page.disabled = self.current_page >= self.max_pages - 1
        self.last_page.disabled = self.current_page >= self.max_pages - 1
        await interaction.response.edit_message(**kwargs)

    @discord.ui.button(emoji="⏪", style=get_button_colour("grey"))
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = 0
        await self.update_page(interaction)

    @discord.ui.button(emoji="◀️", style=get_button_colour("grey"))
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page -= 1
        await self.update_page(interaction)

    @discord.ui.button(emoji="⏹️", style=get_button_colour("grey"))
    async def stop_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.stop()
        await interaction.message.delete()

    @discord.ui.button(emoji="▶️", style=get_button_colour("grey"))
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page += 1
        await self.update_page(interaction)

    @discord.ui.button(emoji="⏩", style=get_button_colour("grey"))
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_page = (self.max_pages - 1)
        await self.update_page(interaction)

    async def start(
        self, obj: Union[commands.Context, discord.Interaction]
    ) -> Optional[Union[Message, InteractionMessage, WebhookMessage]]:
        if isinstance(obj, commands.Context):
            self.context = obj
            self.interaction = None
        else:
            self.context = None
            self.interaction = obj

        if self.message is not None and self.interaction is not None:
            await self.update_page(self.interaction)
        else:
            self.first_page.disabled = self.current_page <= 0
            self.previous_page.disabled = self.current_page <= 0
            kwargs = await self.get_page_kwargs(self.get_page(self.current_page))
            if self.context is not None:
                self.message = await self.context.send(**kwargs)
            elif self.interaction is not None:
                if self.interaction.response.is_done():
                    self.message = await self.interaction.followup.send(**kwargs, view=self)
                else:
                    await self.interaction.response.send_message(**kwargs, view=self)
                    self.message = await self.interaction.original_response()
            else:
                raise RuntimeError(
                    "Cannot start a paginator without a context or interaction.")

        return self.message

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user:
            if await self.context.bot.is_owner(interaction.user):
                return True
            elif interaction.user == self.context.author:
                return True
            else:
                await interaction.response.send_message(content=access_denied(), ephemeral=True)
                return False
        else:
            return True

    async def on_timeout(self):
        for x in self.children:
            x.disabled = True
        await self.message.edit(view=self)
        self.stop()

class NoobConfirmation(discord.ui.View):
    def __init__(self, timeout: Optional[float] = 60.0):
        super().__init__(timeout=timeout)
        self.confirm_action: str = None
        self.context: commands.Context = None
        self.message: discord.Message = None
        self.value = None

    async def start(self, context: commands.Context, confirm_action: str, *args, **kwargs):
        msg = await context.send(view=self, *args, **kwargs)
        self.confirm_action = confirm_action
        self.context = context
        self.message = msg

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        for x in self.children:
            x.disabled = True
        self.value = True
        self.stop()
        await interaction.response.edit_message(content=self.confirm_action, embed=None, view=self)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        for x in self.children:
            x.disabled = True
        self.value = False
        self.stop()
        await interaction.response.edit_message(
            content="Alright not doing that then.", embed=None, view=self
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user:
            if await self.context.bot.is_owner(interaction.user):
                return True
            elif interaction.user == self.context.author:
                return True
            else:
                await interaction.response.send_message(content=access_denied(), ephemeral=True)
                return False
        else:
            return True

    async def on_timeout(self):
        for x in self.children:
            x.disabled = True
        self.stop()
        await self.message.edit(content="You took too long to respond.", embed=None, view=self)
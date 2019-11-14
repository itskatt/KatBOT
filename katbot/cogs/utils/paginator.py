import asyncio
import concurrent.futures
from contextlib import suppress
from textwrap import TextWrapper

import discord
from discord.ext import commands

from . import EMBED_COLOUR


class WrappedPaginator(commands.Paginator):
    def add_line(self, line="", *, empty=False):
        max_size = self.max_size - self._prefix_len - 2

        if len(line) > max_size:
            wrapper = TextWrapper(width=max_size)
            lines = wrapper.wrap(line)
            for l in lines:
                super().add_line(l, empty=empty)
        else:
            super().add_line(line, empty=empty)


class Pages:
    """Implements a paginator that queries the user for the
    pagination interface.

    Pages are 1-index based, not 0-index based.

    If the user does not reply within 2 minutes then the pagination
    interface exits automatically.

    Parameters
    ------------
    ctx: Context
        The context of the command.
    entries: List[str]
        A list of entries to paginate.
    per_page: int
        How many entries show up per page.
    show_entry_count: bool
        Whether to show an entry count in the footer.
    text_paginator: bool
        Whereas this paginator will be a TextPaginator
    stop_deletes: bool
        If the stop button deletes the message

    Attributes
    -----------
    embed: discord.Embed
        The embed object that is being used to send pagination info.
        Feel free to modify this externally. Only the description,
        footer fields, and colour are internally modified.
    permissions: discord.Permissions
        Our permissions for the channel.
    """

    def __init__(self, ctx, *, entries, per_page=12, show_entry_count=True, text_paginator=False, stop_deletes=False):
        self.bot = ctx.bot
        self.entries = entries
        self.message = ctx.message
        self.channel = ctx.channel
        self.author = ctx.author
        self.per_page = per_page
        pages, left_over = divmod(len(self.entries), self.per_page)
        if left_over:
            pages += 1
        self.maximum_pages = pages
        self.embed = discord.Embed(colour=EMBED_COLOUR)
        self.paginating = len(entries) > per_page
        self.show_entry_count = show_entry_count
        self.text_paginator = text_paginator
        self.stop_deletes = stop_deletes
        self.reaction_emojis = [
            # NOTE: do not change the order
            ('\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.first_page),
            ('\N{BLACK LEFT-POINTING TRIANGLE}', self.previous_page),
            ('\N{BLACK RIGHT-POINTING TRIANGLE}', self.next_page),
            ('\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}', self.last_page),
            ('\N{INPUT SYMBOL FOR NUMBERS}', self.numbered_page),
            ('\N{BLACK SQUARE FOR STOP}', self.stop_pages),
            ('\N{INFORMATION SOURCE}', self.show_help),
        ]

        if ctx.guild is not None:
            self.permissions = self.channel.permissions_for(ctx.guild.me)
        else:
            self.permissions = self.channel.permissions_for(ctx.bot.user)

        perm = None
        fmt = ("Je suis désolé, mais cette commande a besoin de la permition **{perm}** pour pouvoir fonctioner"
               " dans ce salon. RDV donc dans vos messages privés (pour éviter cela, contactez un administrateur).")

        if not self.permissions.embed_links and not text_paginator:
            perm = "integrer des liens"

        if not self.permissions.send_messages:
            perm = "envoyer des messages"

        if self.paginating:
            if not self.permissions.add_reactions:
                perm = "ajouter des réactions"

            if not self.permissions.read_message_history:
                perm = "voir les ancients messages"

        if perm:
            self.bot.new_task(ctx.send(fmt.format(perm=perm)))  # TODO: Change bc bad
            if not self.author.dm_channel:
                self.bot.new_task(self.author.create_dm())
            self.channel = self.author.dm_channel

    def get_page(self, page):
        base = (page - 1) * self.per_page
        return self.entries[base:base + self.per_page]

    def get_content(self, entries, page, *, first=False):
        return None

    def get_embed(self, entries, page, *, first=False):
        self.prepare_embed(entries, page, first=first)
        return self.embed

    def prepare_embed(self, entries, page, *, first=False):
        p = []
        for index, entry in enumerate(entries, 1 + ((page - 1) * self.per_page)):
            p.append(f'{index}. {entry}')

        if self.maximum_pages > 1:
            if self.show_entry_count:
                text = f'Page {page}/{self.maximum_pages} ({len(self.entries)} entrées)'
            else:
                text = f'Page {page}/{self.maximum_pages}'

            self.embed.set_footer(text=text)

        if self.paginating and first:
            p.append('')
            p.append("Confus? Reagi avec \N{INFORMATION SOURCE} pour plus d'informations.")

        self.embed.description = '\n'.join(p)

    async def show_page(self, page, *, first=False):
        self.current_page = page
        entries = self.get_page(page)
        content = self.get_content(entries, page, first=first)  # pylint: disable=assignment-from-none
        embed = self.get_embed(entries, page, first=first)

        if not self.paginating:
            self.message = await self.channel.send(content=content, embed=embed)
            return self.message

        if not first:
            await self.message.edit(content=content, embed=embed)
            return

        self.message = await self.channel.send(content=content, embed=embed)
        for (reaction, _) in self.reaction_emojis:
            if self.maximum_pages == 2 and reaction in ('\u23ed', '\u23ee'):
                # no |<< or >>| buttons if we only have two pages
                # we can't forbid it if someone ends up using it but remove
                # it from the default set
                continue

            await self.message.add_reaction(reaction)

    async def checked_show_page(self, page):
        if page != 0 and page <= self.maximum_pages:
            await self.show_page(page)

    async def first_page(self):
        """Va à la première page"""
        await self.show_page(1)

    async def last_page(self):
        """Va à la dernière page"""
        await self.show_page(self.maximum_pages)

    async def next_page(self):
        """Va à la page suivante"""
        await self.checked_show_page(self.current_page + 1)

    async def previous_page(self):
        """Va à la page d'avant"""
        await self.checked_show_page(self.current_page - 1)

    async def show_current_page(self):
        if self.paginating:
            await self.show_page(self.current_page)

    async def numbered_page(self):
        """Permet d'aller a une page directement"""
        to_delete = []
        to_delete.append(await self.channel.send("A quelle page voulez-vous aller?"))

        def message_check(m):
            return m.author == self.author and \
                self.channel == m.channel and \
                m.content.isdigit()

        try:
            msg = await self.bot.wait_for('message', check=message_check, timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(await self.channel.send("Vous avez pris trop de temps."))
            await asyncio.sleep(5)
        else:
            page = int(msg.content)
            to_delete.append(msg)
            if page != 0 and page <= self.maximum_pages:
                await self.show_page(page)
            else:
                to_delete.append(await self.channel.send(f"Cette page n'existe pas. ({page}/{self.maximum_pages})"))
                await asyncio.sleep(5)

        try:
            await self.channel.delete_messages(to_delete)
        except Exception:
            pass

    async def show_help(self):
        """Montre ce message"""
        messages = ["Bienvenue au paginateur interactif!\n"]
        messages.append("Cela vous permet de naviger a traver les pages en utilisant des "
                        'reactions. Les voici:\n')

        for (emoji, func) in self.reaction_emojis:
            messages.append(f'{emoji} {func.__doc__}')

        embed = self.embed.copy()
        embed.clear_fields()
        embed.description = '\n'.join(messages)
        embed.set_footer(text=f'On etait à la page {self.current_page} avant ce message.')
        await self.message.edit(content=None, embed=embed)

        async def go_back_to_current_page():
            await asyncio.sleep(60.0)
            await self.show_current_page()

        self.bot.new_task(go_back_to_current_page())

    async def stop_pages(self):
        """Quite la session de pagination"""
        self.paginating = False
        if self.stop_deletes:
            await self.message.delete()
            return
        try:
            await self.message.clear_reactions()
        except discord.Forbidden:
            for react, _ in self.reaction_emojis:
                await self.message.remove_reaction(react, self.bot.user)

    def react_check(self, reaction, user):
        if user is None or user.id != self.author.id:
            return False

        if reaction.message.id != self.message.id:
            return False

        for (emoji, func) in self.reaction_emojis:
            if reaction.emoji == emoji:
                self.match = func
                return True
        return False

    async def paginate(self):
        """Actually paginate the entries and run the interactive loop if necessary."""
        first_page = self.show_page(1, first=True)
        if not self.paginating:
            await first_page
            if self.text_paginator and self.stop_deletes:
                # react with stop emoji since we would eventually
                # want to delete the paginator message
                await self.message.add_reaction(self.reaction_emojis[5][0])
        else:
            # allow us to react to reactions right away if we're paginating
            self.bot.new_task(first_page)

        while self.paginating or self.stop_deletes:
            done, pending = await asyncio.wait(
                [
                    self.bot.wait_for("reaction_add", check=self.react_check, timeout=120.0),
                    self.bot.wait_for("reaction_remove", check=self.react_check, timeout=120.0)
                ],
                return_when=asyncio.FIRST_COMPLETED)

            try:
                done.pop().result()
            except asyncio.TimeoutError:
                try:
                    if not self.stop_deletes:
                        await self.stop_pages()
                except discord.NotFound:
                    pass
                break
            else:
                for fut in pending:
                    # TODO: fix
                    with suppress(concurrent.futures.TimeoutError()):
                        fut.cancel()

            await self.match()


class FieldPages(Pages):
    """Similar to Pages except entries should be a list of
    tuples having (key, value) to show as embed fields instead.
    """

    def prepare_embed(self, entries, page, *, first=False):
        self.embed.clear_fields()
        self.embed.description = discord.Embed.Empty

        for key, value in entries:
            self.embed.add_field(name=key, value=value, inline=False)

        if self.maximum_pages > 1:
            if self.show_entry_count:
                text = f'Page {page}/{self.maximum_pages} ({len(self.entries)} entrée(s))'
            else:
                text = f'Page {page}/{self.maximum_pages}'

            self.embed.set_footer(text=text)


class TextPages(Pages):
    """Uses a WrappedPaginator internally to paginate some text."""

    def __init__(self, ctx, text, *, prefix='```', suffix='```', max_size=2000, stop_deletes=False):
        paginator = WrappedPaginator(prefix=prefix, suffix=suffix, max_size=max_size - 200)
        for line in text.split('\n'):
            paginator.add_line(line)

        super().__init__(
            ctx,
            entries=paginator.pages,
            per_page=1,
            show_entry_count=False,
            text_paginator=True,
            stop_deletes=stop_deletes
        )

    def get_page(self, page):
        return self.entries[page - 1]

    def get_embed(self, entries, page, *, first=False):
        return None

    def get_content(self, entry, page, *, first=False):
        if self.maximum_pages > 1:
            return f'{entry}\nPage {page}/{self.maximum_pages}'
        return entry


class HelpPaginator(Pages):
    def __init__(self, help_command, ctx, entries, *, per_page=4):
        super().__init__(ctx, entries=entries, per_page=per_page)
        self.reaction_emojis.append(('\N{WHITE QUESTION MARK ORNAMENT}', self.show_bot_help))
        self.total = len(entries)
        self.help_command = help_command
        self.prefix = help_command.clean_prefix

    def get_bot_page(self, page):
        cog, description, commands = self.entries[page - 1]
        self.title = str(cog)
        self.description = description
        return commands

    def prepare_embed(self, entries, page, *, first=False):
        self.embed.clear_fields()
        self.embed.description = self.description
        self.embed.title = self.title

        # if self.get_page is self.get_bot_page:
        #     do 'show support server here' logic

        self.embed.set_footer(text=f'Utilise "{self.prefix}help commande" pour plus d\'infos sur une commande.')

        for entry in entries:
            signature = f'{entry.qualified_name} {entry.signature}'
            self.embed.add_field(name=signature, value=entry.short_doc or "Pas d'aide precisée", inline=False)

        if self.maximum_pages:
            self.embed.set_author(name=f'Page {page}/{self.maximum_pages} ({self.total} commandes)')

    async def show_help(self):
        """Montre ce message"""

        self.embed.title = 'Aide du paginateur'
        self.embed.description = "Bienvenue a la page d'aide!"

        messages = [f'{emoji} {func.__doc__}' for emoji, func in self.reaction_emojis]
        self.embed.clear_fields()
        self.embed.add_field(name='A quoi servent ces réactions?', value='\n'.join(messages), inline=False)

        self.embed.set_footer(text=f'On était a la page {self.current_page} avant ce message.')
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_current_page()

        self.bot.new_task(go_back_to_current_page())

    async def show_bot_help(self):
        """Montre comment utiliser le bot"""

        self.embed.title = "Utilisation du bot"
        self.embed.description = "Bienvenue a la page d'aide des commandes!"
        self.embed.clear_fields()

        entries = (
            ('<argument>', 'Cet argument est __**requis**__.'),
            ('[argument]', 'Cet argument est __**facultatif**__.'),
            ('[A|B]', 'Cela peut être __**A or B**__.'),
            ('[argument...]', 'Plusieurs arguments sont attendus.\n'
                              'Maintenant que tu est familier avec les base, il est important de noter que...\n'
                              '__**Il ne faut pas écrire <> et []!!!**__')
        )

        self.embed.add_field(name='Comment utiliser les commandes du bot?', value="C'est très simple:")

        for name, value in entries:
            self.embed.add_field(name=name, value=value, inline=False)

        self.embed.set_footer(text=f'On était a la page {self.current_page} avant ce message.')
        await self.message.edit(embed=self.embed)

        async def go_back_to_current_page():
            await asyncio.sleep(30.0)
            await self.show_current_page()

        self.bot.new_task(go_back_to_current_page())

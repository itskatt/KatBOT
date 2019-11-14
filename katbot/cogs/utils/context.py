import asyncio
import random

import discord
from discord.ext import commands


class LoadingManager(discord.context_managers.Typing):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.ctx = ctx
        self.rle = random.choice(self.ctx.bot.loading_emotes)

    async def __aenter__(self):
        self.msg = await self.ctx.send(f"<{self.rle}>")
        return await super().__aenter__()

    async def __aexit__(self, type_, value, traceback):
        await self.msg.delete()
        await super().__aexit__(type_, value, traceback)

    async def update(self, msg):
        await self.msg.edit(content=f"<{self.rle}> **|** {msg}")


class Ctx(commands.Context):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def tick(self, state=True):
        if state:
            try:
                await self.message.add_reaction("\U00002611")
            except (discord.Forbidden, discord.HTTPException):
                pass
        elif not state:
            try:
                await self.message.add_reaction("\U0001f4a2")
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def add_delete_reaction(self, message=None):
        msg = message or self.message
        reaction = "\U0001f6d1"  # 🛑

        try:
            await msg.add_reaction(reaction)
        except (discord.Forbidden, discord.HTTPException):
            return

        def check(react, user):
            return (user == self.author) and \
                   (str(react.emoji) == reaction) and \
                   (react.message.id == msg.id)

        try:
            await self.bot.wait_for("reaction_add", timeout=20, check=check)
        except asyncio.TimeoutError:
            await msg.remove_reaction(reaction, self.me)
        else:
            await msg.delete()

    async def add_new_reaction(self, message=None):
        msg = message or self.message
        emote = "\N{SQUARED NEW}"

        await msg.add_reaction(emote)

        def check(react, user):
            return (user == self.author) and \
                   (str(react.emoji) == emote) and \
                   (react.message.id == msg.id)

        try:
            await self.bot.wait_for("reaction_add", timeout=20, check=check)
        except asyncio.TimeoutError:
            await msg.remove_reaction(emote, self.me)
        else:
            await self.invoke(self.command)

    async def dm(self, *args, **kwargs):
        try:
            return await self.author.send(*args, **kwargs)
        except discord.Forbidden:
            return None

    def loading(self):
        return LoadingManager(self)

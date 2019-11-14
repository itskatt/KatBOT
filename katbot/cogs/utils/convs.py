import json

import discord
from discord.ext import commands

from . import EMOJI_REGEX, datapath

IMAGE_FORMATS = ('png', 'jpg', 'jpeg', 'webp')

with open(datapath("emojis.json"), "r", encoding="utf=8") as f:
    EMOJIS = json.load(f)


class MemberConvFail(commands.BadArgument):
    pass


class UserConvFail(commands.BadArgument):
    pass


class ImageNotFound(Exception):
    pass


class MemberConv(commands.Converter):
    async def convert(self, ctx, potential_member):
        try:
            member = await commands.MemberConverter().convert(ctx, potential_member)
            return member
        except commands.BadArgument:
            e = MemberConvFail(f"Member {potential_member} not found.")
            e.member = potential_member
            raise e


class UserConv(commands.Converter):
    async def convert(self, ctx, potential_user):
        try:
            user = await commands.UserConverter().convert(ctx, potential_user)
            return user
        except commands.BadArgument:
            if potential_user.isdigit():  # The provided user is an id
                if len(potential_user) == 18:  # Make sure its valid
                    potential_user = int(potential_user)
                    try:
                        user = await ctx.bot.fetch_user(potential_user)  # Try to get it...
                        return user
                    except discord.NotFound:  # Didnt got it, so raise
                        pass
            e = UserConvFail(f"User {potential_user} not found.")
            e.user = potential_user
            raise e


class UnionMemberUser(commands.Converter):
    async def convert(self, ctx, potential_user):
        try:
            member = await MemberConv().convert(ctx, potential_user)
            return member
        except MemberConvFail:
            try:
                user = await UserConv().convert(ctx, potential_user)
                return user
            except UserConvFail:
                e = UserConvFail(f"User {potential_user} not found.")
                e.user = potential_user
                raise e


class GetImg(commands.Converter):
    async def convert(self, ctx, item):
        emoji = self.is_emoji(ctx, item)
        if emoji:
            return emoji

        # check if item is user mention
        try:
            user = await UserConv().convert(ctx, item)
        except UserConvFail:
            pass
        else:
            return str(user.avatar_url_as(format="png", size=256))

        # check if item is url
        if item.startswith("<") and item.endswith(">"):
            item = item[1:-1]
        if item.startswith(
            ("https://cdn.discordapp.com", "https://media.discordapp.net")
        ):
            url = self.check_extension(item)
            if url:
                return item

        ret = await self.from_history(ctx)
        if ret:
            return ret

        # We shouldn't get here
        raise ImageNotFound("No image found.")

    def is_emoji(self, ctx, item):
        # check if item is custom emoji
        emoji_match = EMOJI_REGEX.fullmatch(item)
        if emoji_match:
            groups = emoji_match.groupdict()
            emote_id = int(groups["id"])
            animated = bool(groups["animated"])

            emote = None
            if not animated:
                emote = ctx.bot.get_emoji(emote_id)

            if emote:
                return str(emote.url)
            elif not animated:
                # If not build the url manualy and do with it
                return f"https://cdn.discordapp.com/emojis/{emote_id}.png"

        # check if item is standard emoji
        if item.strip() in EMOJIS:
            code = "-".join(map(lambda c: f"{ord(c):x}", item))
            return f"https://bot.mods.nyc/twemoji/{code}.png"

        return

    async def from_history(self, ctx):
        # check channel history for attachments
        history = await ctx.channel.history(limit=100, before=ctx.message.created_at).flatten()

        for m in [ctx.message] + history:
            # check attachments (files uploaded to discord)
            for attachment in m.attachments:
                extension = self.check_extension(attachment.filename)
                if not extension:
                    continue
                return attachment.url

            # check embeds (user posted url / bot posted rich embed)
            for embed in m.embeds:
                if embed.image:
                    extension = self.check_extension(embed.image.proxy_url)
                    if extension:
                        return embed.image.proxy_url

                # bot condition because we do not want image from
                # rich embed thumbnail
                if not embed.thumbnail or (m.author.bot and embed.type == "rich"):
                    continue

                # avoid case when image embed was created from url that is
                # used as argument or flag
                if m.id == ctx.message.id:
                    if embed.thumbnail.url in m.content:
                        continue

                extension = self.check_extension(embed.thumbnail.proxy_url)
                if not extension:
                    continue

                return embed.thumbnail.proxy_url

    def check_extension(self, url):
        extension = url.rpartition('.')[-1].lower()
        if extension not in IMAGE_FORMATS:
            return
        return extension

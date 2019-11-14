import json
import random
import unicodedata
from difflib import SequenceMatcher
from urllib.parse import quote_plus

import discord
from discord.ext import commands

from .utils import EMBED_COLOUR, datapath
from .utils.convs import GetImg
from .utils.paginator import Pages

with open(datapath("blagues.json"), "r", encoding="utf=8") as f:
    BLAGUES = json.load(f)


class Misc(commands.Cog):
    """Des commandes a buts variés."""

    def __init__(self, bot):
        self.bot = bot
        self.reg_map = {
            "z": "\ud83c\uddff",
            "y": "\ud83c\uddfe",
            "x": "\ud83c\uddfd",
            "w": "\ud83c\uddfc",
            "v": "\ud83c\uddfb",
            "u": "\ud83c\uddfa",
            "t": "\ud83c\uddf9",
            "s": "\ud83c\uddf8",
            "r": "\ud83c\uddf7",
            "q": "\ud83c\uddf6",
            "p": "\ud83c\uddf5",
            "o": "\ud83c\uddf4",
            "n": "\ud83c\uddf3",
            "m": "\ud83c\uddf2",
            "l": "\ud83c\uddf1",
            "k": "\ud83c\uddf0",
            "j": "\ud83c\uddef",
            "i": "\ud83c\uddee",
            "h": "\ud83c\udded",
            "g": "\ud83c\uddec",
            "f": "\ud83c\uddeb",
            "e": "\ud83c\uddea",
            "d": "\ud83c\udde9",
            "c": "\ud83c\udde8",
            "b": "\ud83c\udde7",
            "a": "\ud83c\udde6",
        }

    @commands.command(aliases=["g2"])
    async def google2(self, ctx, *, recherche):
        """
        Pour ceux qui ne savent pas comment utiliser google...
        """
        base = "https://lmgtfy.com/?q={}"

        await ctx.send(base.format(quote_plus(recherche)))

    # Custom emotes command
    @commands.group(name="emoji", aliases=["e"], invoke_without_command=True)
    async def emoji_(self, ctx, emoji: str):
        """Commandes d'emojis."""
        em_map = {emoj.name: emoj for emoj in self.bot.emojis}

        try:
            e = em_map[emoji]
        except KeyError:
            pass
        else:
            return await ctx.send(str(e))

        em_lst = []
        for e in em_map:
            em_lst.append((
                em_map[e],
                SequenceMatcher(None, emoji, e).ratio()
            ))

        em_lst = (sorted(em_lst, key=lambda em: em[1], reverse=True))[:3]

        if em_lst[0][1] > 90.0:
            return await ctx.send(
                str(em_lst[0][0])
            )

        # TODO finish fmt
        em_lst = "\n    -".join(
            [f"{e} **-** {e.name}" for e, _ in em_lst]
        )

        fmt = (
            f"Je n'ai pas pu trouver l'émoji *\"{emoji}\"*.\n"
            "Vous vouliez peut être dire:"
            f"\n    -{em_lst}"
        )
        await ctx.send(fmt)

    @emoji_.command(name="liste", aliases=["ls", "list"])
    async def emoji_liste(self, ctx):
        """
        Montre les emojis que je peux voir.
        """
        el = []
        for e in sorted(self.bot.emojis, key=lambda e: e.name):
            el.append(f"{e} **-** {e.name}")

        p = Pages(ctx=ctx, entries=el)
        await p.paginate()

    @commands.command()
    async def blague(self, ctx):
        """
        Dis une blague pas drôle.
        """
        await ctx.send(random.choice(BLAGUES))

    # Text to regional indicator command
    @commands.command(aliases=["el"])
    async def emojilettres(self, ctx, *, texte: commands.clean_content):
        """
        Permet de parler 🇨​🇴​🇲​🇲​🇪​ 🇨​🇦​
        """
        texte = texte.lower()
        out = []

        for char in texte:
            if char in "qwertyuiopasdfghjklzxcvbnm":
                out.append(self.reg_map[char])
                out.append("\u200b")
            else:
                out.append(char)

        out = "".join(out)
        if len(out) > 2000:
            await ctx.send(await self.bot.safe_bin_post(out))
        else:
            await ctx.send(out)

    @commands.command(name="\U0001f171")
    async def b_fy(self, ctx, *, texte: str):
        """
        🅿ermet de 🅿🅰rler c⭕mme ç🅰
        """
        texte = texte.replace("a", "\U0001f170")
        texte = texte.replace("b", "\U0001f171")
        texte = texte.replace("o", "\U00002b55")
        texte = texte.replace("p", "\U0001f17f")

        await ctx.send(texte)

    @commands.command(aliases=["bigmoji"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def gros_emoji(self, ctx, emoji):
        """
        Renvoie l'image d'un emoji.
        """
        async with ctx.typing():
            e = GetImg().is_emoji(ctx, emoji)
            if e:
                img = await self.bot.sget(e, buffer=True)
                await ctx.send(file=discord.File(img, "emoji.png"))
            else:
                await ctx.send("Je ne connais pas cet emoji, desolé...")

    @commands.command(aliases=["ld", "fermer"])
    @commands.has_permissions(administrator=True)
    async def lockdown(self, ctx):
        """
        Permet de fermer un salon. Vous devez etre Administrateur pour pouvoir utiliser cette commande.
        """
        perms = ctx.channel.overwrites_for(ctx.guild.default_role)
        if perms.send_messages is False:  # Already locked
            perms.send_messages = None
            await ctx.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=perms
            )
            await ctx.send("Ce salon est maintenant **ouvert**.")
        else:
            perms.send_messages = False
            await ctx.channel.set_permissions(
                ctx.guild.default_role,
                overwrite=perms
            )
            await ctx.send("Ce salon a été **fermé**.\nPour le réouvrir, re-utilisez cette commande.")

    # Snipe command
    @commands.command()
    async def snipe(self, ctx):
        """Montre le dernier message suprimé de ce salon."""
        try:
            data = self.bot.snipe_data[ctx.channel.id]
        except KeyError:
            await ctx.send(
                "Je n'ai pas enregistré de supressions de"
                "messages pour ce salon."
            )
        else:
            embed = discord.Embed(
                color=EMBED_COLOUR,
                description=data["content"],
                timestamp=data["timestamp"]
            )
            # We try to update the author's info
            author = self.bot.get_user(data["author"].id)
            if not author:
                author = data["author"]
            embed.set_author(
                name=str(author),
                icon_url=author.avatar_url_as(format="png")
            )
            # Try to get the image if there is (still) one
            if data["image"]:
                try:
                    embed.set_image(url=data["image"].proxy_url)
                except discord.NotFound:
                    pass
            embed.set_footer(text=f"Message suprimé")
            await ctx.send(embed=embed)

    # Charinfo
    @commands.command(aliases=["ci"])
    async def charinfo(self, ctx, *, characters: str):
        """Donne des info sur un ou des charactère."""

        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Non trouvé.')
            return (f"`\\U{digit:>08}`: {name} - {c} \N{EM DASH} "
                    f"<http://www.fileformat.info/info/unicode/char/{digit}>")

        msg = '\n'.join(map(to_string, characters))
        if len(msg) > 2000:
            return await ctx.send(await self.bot.safe_bin_post(msg))
        await ctx.send(msg)

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def fmsg(self, ctx):
        """
        Montre le premier message envoyé dans le salon actuel.
        """
        await ctx.trigger_typing()
        async for msg in ctx.channel.history(
            limit=1,
            after=ctx.channel.created_at
        ):
            e = discord.Embed(
                color=EMBED_COLOUR,
                description=msg.content
            )
            e.set_author(
                name=str(msg.author),
                icon_url=msg.author.avatar_url
            )
            e.add_field(
                name="Message original",
                value=f"[Go!]({msg.jump_url})"
            )
            await ctx.send(embed=e)

    @commands.command()
    async def clap(self, ctx, *, texte: str):
        await ctx.send(
            "\U0001f44f".join(texte.split(" "))
        )

    @commands.command(aliases=["msg", "msgraw", "raw"])
    async def rawmsg(self, ctx, message: discord.Message):
        """
        Montre un message Discord sous sa forme en JSON
        """
        msg = await self.bot.http.get_message(ctx.channel.id, message.id)
        msg = json.dumps(msg, indent=2)
        if len(msg) > 1985:
            return await ctx.send(await self.bot.safe_bin_post(msg))
        await ctx.send(f"```json\n{msg}\n```")


def setup(bot):
    bot.add_cog(Misc(bot))

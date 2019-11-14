import asyncio
from datetime import datetime
from io import BytesIO
from urllib.parse import quote_plus

import async_cse
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType

from config import GOOGLE_CSE_KEY, SCREENSHOTLAYER_KEY

from .utils import EMBED_COLOUR, URL_REGEX


class Apis(commands.Cog):
    """Des commandes en rapport avec les apis."""

    def __init__(self, bot):
        self.bot = bot
        self.google = async_cse.Search(
            GOOGLE_CSE_KEY,
            session=bot.session
        )
        self.fail_msg = ("Une erreur s'est produite, veuiller réesayer.\n"
                         "*Si ce message persiste, alors veillez réessayer plus tard.*")

    # Google command
    @commands.command(name="google", aliases=['g'])
    @commands.cooldown(1, 15, BucketType.user)
    async def google_(self, ctx, *, recherche: str):
        """Recherche quelque chose sur google."""
        async with ctx.typing():
            try:
                r = (await self.google.search(recherche))[0]
            except async_cse.NoResults:
                return await ctx.send("Je n'ai rien trouvé...")
            except (async_cse.NoMoreRequests, async_cse.APIError):
                return await ctx.send(
                    "Une erreur interne est survenue, veillez essayer plus tard."
                )
            else:
                e = discord.Embed(
                    title=r.title,
                    description=r.description,
                    color=EMBED_COLOUR,
                    url=r.url
                )
                url = ctx.author.avatar_url_as(static_format="png", size=128)
                e.set_footer(text="Demandé par {}".format(
                    ctx.author), icon_url=url)
                e.set_image(url=r.image_url)
                await ctx.send("**Voila ce que j'ai trouvé:**", embed=e)

    # Random cat!
    @commands.command(aliases=["cat"])
    @commands.cooldown(1, 2, BucketType.user)
    async def chat(self, ctx):
        """Poste une image aleatoire de chat!"""
        await ctx.trigger_typing()
        url = await self.bot.sget("http://aws.random.cat/meow", json="file")

        embed = discord.Embed(color=EMBED_COLOUR)
        embed.add_field(name="Miaou! \U0001f63b", value="\uFEFF")
        embed.set_image(url=url)
        embed.timestamp = datetime.utcnow()
        m = await ctx.send(embed=embed)
        await asyncio.sleep(1)
        await ctx.add_new_reaction(m)

    # Random dog!
    @commands.command(aliases=["dog"])
    @commands.cooldown(1, 2, BucketType.user)
    async def chien(self, ctx):
        """Poste une image aleatoire de chien!"""
        await ctx.trigger_typing()
        await ctx.trigger_typing()
        url = await self.bot.sget("https://random.dog/woof.json", json="url")

        embed = discord.Embed(color=EMBED_COLOUR)
        embed.add_field(name="Waf! \U0001f436", value="\uFEFF")
        embed.set_image(url=url)
        embed.timestamp = datetime.utcnow()
        m = await ctx.send(embed=embed)
        await asyncio.sleep(1)
        await ctx.add_new_reaction(m)

    # Random fox!
    @commands.command(aliases=["fox"])
    @commands.cooldown(1, 2, BucketType.user)
    async def renard(self, ctx):
        """Poste une image aleatoire de renard!"""
        await ctx.trigger_typing()
        url = await self.bot.sget("https://randomfox.ca/floof", json="image", trust_host=True)

        embed = discord.Embed(color=EMBED_COLOUR)
        embed.add_field(name="Floof! \U0001f98a", value="\uFEFF")
        embed.set_image(url=url)
        embed.timestamp = datetime.utcnow()
        m = await ctx.send(embed=embed)
        await asyncio.sleep(1)
        await ctx.add_new_reaction(m)

    # Calculation command
    @commands.command(aliases=["calc"])
    @commands.cooldown(1, 3, BucketType.user)
    async def calculer(self, ctx, *, calcul):
        """
        Permet de calculer une expression algébrique.
        Les conversions d'unités sont aussi suportées.
        """
        await ctx.trigger_typing()
        url = f"http://api.mathjs.org/v4/?expr={quote_plus(calcul)}"
        async with self.bot.session.get(url) as r:
            if r.status == 200:
                resp = await r.text()
                await ctx.send(f"`{calcul} =` **{resp}**")
            elif r.status == 400:
                resp = await r.text()
                await ctx.send(f"**__Erreur!__**\n```{resp}```")
            else:
                await ctx.send(self.fail_msg)

    # Qr code generator cmd
    @commands.command()
    @commands.cooldown(1, 5, BucketType.user)
    async def qr(self, ctx, *, texte):
        """Génére un code qr."""
        url = (
            f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={quote_plus(texte)}"
        )
        await ctx.trigger_typing()
        resp = await self.bot.sget(url, buffer=True)
        await ctx.send(
            "Votre code qr:",
            file=discord.File(resp, "qr.png")
        )

    # Webpage screenshot command
    @commands.group(aliases=["ss"])
    @commands.cooldown(1, 30, BucketType.channel)
    async def screenshot(self, ctx, site: str, delai: int = 1, pleine_page: int = 0):
        """
        Prend une capture d'écran d'un site internet.
        __Paramètres:__
            `delai` signifie combien de temps attendre avant de prendre la capture d'écran.
            `pleine_page` si on veux prendre toute la page *(1)* ou non *(0)*.
        """
        if site.startswith("https://"):
            site.replace("https://", "http://", 1)
        elif site.startswith("http://"):
            pass
        if not URL_REGEX.fullmatch(site):
            return await ctx.send("URL non valide.")

        site_enc = quote_plus(site)

        if delai < 0 or delai > 10:
            return await ctx.send(f"Le delai doit être entre 0 et 10 secondes, pas {delai}.")

        if pleine_page not in [0, 1]:
            return await ctx.send(f"Expectait 0 ou 1 pour `pleine_page`, pas {pleine_page}.")

        url = (
            f"http://api.screenshotlayer.com/api/capture?access_key={SCREENSHOTLAYER_KEY}&url={site_enc}"
        )
        params = {
            'fullpage': str(pleine_page),
            'viewport': '1440x900',
            'delay': str(delai),
            'ttl': '300',
            'force': '1',
            'accept_lang': 'fr',
        }

        async with ctx.typing():
            async with self.bot.session.get(url, params=params) as r:
                if r.status == 200:
                    if "image" not in r.headers["Content-Type"]:
                        return await ctx.send(self.fail_msg)

                    io_strm_img = BytesIO(await r.read())
                    embed = discord.Embed(
                        color=EMBED_COLOUR,
                        title=f"Screenshot de {site}:",
                        url=site
                    )
                    embed.set_image(url="attachment://screenshot.png")
                    embed.set_footer(
                        text=f"Demandé par {ctx.author}",
                        icon_url=ctx.author.avatar_url_as(
                            static_format="png",
                            size=128
                        )
                    )
                    await ctx.send(
                        embed=embed,
                        file=discord.File(io_strm_img, "screenshot.png")
                    )
                else:
                    await ctx.send(self.fail_msg)


def setup(bot):
    bot.add_cog(Apis(bot))

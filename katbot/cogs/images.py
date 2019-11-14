import asyncio
import colorsys
import io
import math
import os
import random
import time
from io import BytesIO

import discord
import numpy as np
from async_timeout import timeout as Timeout
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from PIL import Image, ImageDraw

from .utils.convs import GetImg, MemberConv
from .utils import datapath

BIG_CHAR_MAP = " .\\'^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
SMALL_CHAR_MAP = " .:-=+*#%@"
SHADE_CHAR_MAP = " ░▒▓█"
BOX_CHAR_MAP = " □■"

CHAR_MAPS = (
    BIG_CHAR_MAP,
    SMALL_CHAR_MAP,
    SHADE_CHAR_MAP,
    BOX_CHAR_MAP
)


def lum(rgb):
    """
    Returns the luminosity of a pixel
    """
    r, g, b = rgb
    return math.sqrt(.241 * r + .691 * g + .068 * b)


def get_pixels(img):
    pixels = []
    pos = 0
    for p in list(img.getdata()):
        pix = Pixel(p)
        pix.pos = pos
        pos += 1
        pixels.append(pix)

    return pixels


class Pixel:
    def __init__(self, rgb):
        self.rgb = rgb
        self.sorter = lum(rgb)

        self.pos = None
        self.new = None


class Images(commands.Cog):
    """
    Des commandes de manipulation d'images.
    """

    def __init__(self, bot):
        self.bot = bot

    async def get_avatar(self, user):
        avatar_url = str(user.avatar_url_as(format="png", size=256))

        async with self.bot.session.get(avatar_url) as response:
            avatar_bytes = await response.read()

        return avatar_bytes

    @staticmethod
    def process_nyan(avatar_bytes):
        with Image.open(BytesIO(avatar_bytes)) as im:
            locations = [
                (128, 63),  # Frame 1 position
                (128, 63),  # etc...
                (131, 65),
                (131, 65),
                (128, 65),
                (128, 63),
                (128, 64),
                (131, 65),
            ]
            frames = []
            fn = 0
            for loc in locations:
                fn = fn + 1

                with Image.open(datapath(
                        "nyan frames",
                        f"nyan_frame_ ({fn}).jpg")) as support:

                    im = im.resize((40, 40))
                    try:
                        support.paste(im, loc, im)
                    except Exception:
                        support.paste(im, loc)

                    frames.append(support)

                final_buffer = BytesIO()

                frames[0].save(
                    final_buffer,
                    "gif",
                    save_all=True,
                    append_images=frames[1:],
                    duration=100,
                    loop=0
                )

        final_buffer.seek(0)

        return final_buffer

    @staticmethod
    def process_circle(avatar_bytes: bytes, colour: tuple) -> BytesIO:

        # we must use BytesIO to load the image here as PIL expects a stream instead of
        # just raw bytes.
        with Image.open(BytesIO(avatar_bytes)) as im:
            # this creates a new image the same size as the user's avatar, with the
            # background colour being the user's colour.
            with Image.new("RGB", im.size, colour) as background:
                # this ensures that the user's avatar lacks an alpha channel, as we're
                # going to be substituting our own here.
                rgb_avatar = im.convert("RGB")
                # this is the mask image we will be using to create the circle cutout
                # effect on the avatar.
                with Image.new("L", im.size, 0) as mask:
                    # ImageDraw lets us draw on the image, in this instance, we will be
                    # using it to draw a white circle on the mask image.
                    mask_draw = ImageDraw.Draw(mask)
                    # draw the white circle from 0, 0 to the bottom right corner of the image
                    mask_draw.ellipse([(0, 0), im.size], fill=255)
                    # paste the alpha-less avatar on the background using the new circle mask
                    # we just created.
                    background.paste(rgb_avatar, (0, 0), mask=mask)
                # prepare the stream to save this image into
                final_buffer = BytesIO()
                # save into the stream, using png format.
                background.save(final_buffer, "png")
        # seek back to the start of the stream
        final_buffer.seek(0)

        return final_buffer

    @staticmethod
    def process_grab(buff):
        with Image.open(BytesIO(buff)) as avy:
            if avy.mode != 'RGBA':
                avy = avy.convert('RGBA')

            width, height = avy.size

            # Gradient part
            with Image.new('L', (1, height), color=0xFF) as gradient:
                for x in range(height):
                    gradient.putpixel((0, x), 450 - x)

                alpha = gradient.resize(avy.size)
            with Image.new('RGBA', (width, height), color=0) as black_im:  # black
                black_im.putalpha(alpha)

            with Image.alpha_composite(avy, black_im) as gradient_im:

                # Pasting part
                with Image.open(datapath("grab", "grab_top.png")) as top:
                    gradient_im = gradient_im.resize([175] * 2)
                    top.paste(gradient_im, (218, 0))

                    buff = BytesIO()

                    top.save(buff, "PNG")

        buff.seek(0)
        return buff

    @staticmethod
    def process_random_color(method):
        if method == "hsv":
            values = tuple([int(x * 255) for x in colorsys.hsv_to_rgb(random.random(), 1, 1)])
        elif method == "hex":
            values = tuple([random.randint(0, 255) for _ in range(3)])

        with Image.new("RGB", (75, 75), values) as img:
            buff = io.BytesIO()
            img.save(buff, "png")
        buff.seek(0)
        return buff, "#{0:02x}{1:02x}{2:02x}".format(*values)

    @staticmethod
    def process_sort(data):
        with Image.open(BytesIO(data)) as img:
            # TODO: decide if i should keep this
            # if img.mode != "RGB":
            #     img = img.convert("RGB")

            # Convert the image to an array
            arr = np.array(img)

        shape = arr.shape
        # Sort the images pixels
        arr = arr.reshape((shape[0] * shape[1], shape[2]))
        arr.sort(0)

        with Image.fromarray(arr.reshape(shape)) as new:
            # we can now save the image back
            buff = BytesIO()
            new.save(buff, "png")

        buff.seek(0)
        return buff

    @staticmethod
    def process_way_sort(data, way):
        with Image.open(BytesIO(data)) as img:
            arr = np.array(img)

        arr.sort(way)  # 0: vertical | 1: horizontal

        with Image.fromarray(arr) as new:
            buff = BytesIO()
            new.save(buff, "png")

        buff.seek(0)
        return buff

    @staticmethod
    def process_sorting(data):
        # NOTE: hight resolution images will output LARGE files
        with Image.open(BytesIO(data)) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            size = img.width * img.height
            if size > 65536:
                img.thumbnail((256, 256))

            arr = np.array(img)
        shape = arr.shape

        npixs = shape[0] * shape[1]
        valid = []
        for i in range(1, npixs + 1):
            num = npixs / i
            if num.is_integer():
                valid.append((int(num), i))

        frames = []
        for v in valid:
            arr = arr.reshape((v[0], v[1], shape[2]))
            arr.sort(1)

            with Image.fromarray(arr.reshape(shape)) as new:
                frames.append(new)

        buff = BytesIO()
        frames[0].save(
            buff,
            "gif",
            save_all=True,
            append_images=frames[1:] + frames[-1:] * 5,
            duration=125,
            loop=0
        )
        buff.seek(0)
        return buff

    @staticmethod
    def process_colormap(in_):
        # Image model
        with Image.open(BytesIO(in_[1])) as img_model:
            if img_model.mode != "RGB":
                img_model = img_model.convert("RGB")

            width, height = img_model.size
            model = get_pixels(img_model)

        model.sort(key=lambda pix: pix.sorter)

        # Color source
        with Image.open(BytesIO(in_[0])) as img_source:
            if img_source.mode != "RGB":
                img_source = img_source.convert("RGB")

            if not img_model.size == img_source.size:
                img_source = img_source.resize((width, height))
            csource = get_pixels(img_source)

        csource.sort(key=lambda pix: pix.sorter)

        # track the first's image equivalent pixels
        # to the second image
        for i, pix in enumerate(csource):
            model[i].new = pix.rgb

        # sort the second image back by original position
        model.sort(key=lambda pix: pix.pos)
        pixels = [pix.new for pix in model]

        with Image.new("RGB", (width, height)) as new:
            new.putdata(pixels)

            buff = BytesIO()
            new.save(buff, "png")

        buff.seek(0)
        return buff

    @staticmethod
    def process_ascii(data, cmap, is_big=False):
        with Image.open(BytesIO(data)) as img:
            if not is_big:
                img.thumbnail((44, 44))
            if img.mode != "L":
                img = img.convert("L")
            arr = np.array(img)

        char_map = CHAR_MAPS[cmap]
        ascii_art = ""
        for i_row in range(0, arr.shape[0], 2):
            row = arr[i_row]
            for col in row:
                ascii_art += char_map[int(col / (255 / len(char_map))) - 1]
            ascii_art += "\n"
        return ascii_art

    @commands.command()
    @commands.cooldown(1, 15, BucketType.user)
    async def nyan(self, ctx, *, objet: GetImg = None):
        """Deviend le Nyan cat."""
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.time()
            buff = await self.bot.in_thread(self.process_nyan, objet)
            file_ = discord.File(filename="nyan.gif", fp=buff)
            time_ = time.time() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*", file=file_)

    @commands.command()
    @commands.cooldown(1, 10, BucketType.user)
    async def cercle(self, ctx, *, membre: MemberConv = None):
        """Montre l'avatar du membre specifié dans un rond sur sa couleur."""

        membre = membre or ctx.author
        time_ = time.time()

        async with ctx.loading() as load:
            if isinstance(membre, discord.Member):
                member_colour = membre.colour.to_rgb()
            else:
                member_colour = (0, 0, 0)

            await load.update("Téléchargement de l'image...")
            avatar_bytes = await self.get_avatar(membre)

            await load.update("Traitement...")
            final_buffer = await self.bot.in_thread(self.process_circle, avatar_bytes, member_colour)
            file_ = discord.File(filename="cercle.png", fp=final_buffer)
            time_ = time.time() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*", file=file_)

    @commands.command()
    @commands.cooldown(1, 10, BucketType.user)
    async def grab(self, ctx, *, objet: GetImg = None):
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            buff = await self.bot.in_thread(self.process_grab, objet)
            files = [
                discord.File(filename="top.png", fp=buff),
                discord.File(fp=datapath("grab", "grab_bottom.jpg"), filename="down.jpg")
            ]
            await load.update("Envoi...")
            await ctx.send(files=files)

    @commands.command(aliases=["couleur_aleatoire", "coulat", "randc", "ca", "rc"])
    @commands.cooldown(1, 2, BucketType.user)
    async def random_color(self, ctx):
        """
        Créé une image avec une couleur aleatoire.
        """
        buff, code = await self.bot.in_thread(self.process_random_color, "hsv")
        await ctx.send(code, file=discord.File(buff, "random.png"))

    @commands.command(aliases=["couleur_aleatoire2", "coulat2", "randc2", "ca2", "rc2"])
    @commands.cooldown(1, 2, BucketType.user)
    async def random_color2(self, ctx):
        """
        Créé une image avec une couleur aleatoire en utilisant une autre methode.
        """
        buff, code = await self.bot.in_thread(self.process_random_color, "hex")
        await ctx.send(code, file=discord.File(buff, "random.png"))

    @commands.group(aliases=["sort"], invoke_without_command=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def trie(self, ctx, *, objet: GetImg = None):
        """
        Trie les pixels d'une image.
        """
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.perf_counter()
            buff = await self.bot.in_thread(self.process_sort, objet)
            time_ = time.perf_counter() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*", file=discord.File(buff, "sorted.png"))

    @trie.command(name="vertical", aliases=["v"])
    @commands.cooldown(1, 10, BucketType.user)
    async def trie_vertical(self, ctx, *, objet: GetImg = None):
        """
        Trie les pixels d'une image verticalement.
        """
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.perf_counter()
            buff = await self.bot.in_thread(self.process_way_sort, objet, 0)
            time_ = time.perf_counter() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*", file=discord.File(buff, "sorted.png"))

    @trie.command(name="horizontal", aliases=["h"])
    @commands.cooldown(1, 10, BucketType.user)
    async def trie_horizontal(self, ctx, *, objet: GetImg = None):
        """
        Trie les pixels d'une image horizontalement.
        """
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.perf_counter()
            buff = await self.bot.in_thread(self.process_way_sort, objet, 1)
            time_ = time.perf_counter() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*", file=discord.File(buff, "sorted.png"))

    @commands.command(aliases=["sorting"])
    @commands.cooldown(1, 20, BucketType.channel)
    async def triant(self, ctx, *, objet: GetImg = None):
        """
        Visualise (entre-autres) le trie des pixels d'une image.
        """
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.perf_counter()
            buff = await self.bot.in_thread(self.process_sorting, objet, thread=True)
            time_ = time.perf_counter() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_, 3)}s:*", file=discord.File(buff, "sorting.gif"))

    @commands.command(aliases=["colormap"])
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def transforme(self, ctx, source: GetImg = None, model: GetImg = None):
        # TODO: proper help msg
        source = source or str(ctx.author.avatar_url_as(format="png", size=256))
        model = model or str(self.bot.user.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement des images (1/2)...")
            in_ = []
            in_.append(await self.bot.sget(source))

            await load.update("Téléchargement des images (2/2)...")
            in_.append(await self.bot.sget(model))

            await load.update("Traitement...")
            time_ = time.perf_counter()
            buff = await self.bot.in_thread(self.process_colormap, in_)
            time_ = time.perf_counter() - time_

            await load.update("Envoi...")
            await ctx.send(f"*En {round(time_, 3)}s:*", file=discord.File(buff, "colormap.png"))

    async def do_ascii_cmd(self, ctx, objet, cmap, *, is_big=False):
        objet = objet or str(ctx.author.avatar_url_as(format="png", size=256))

        async with ctx.loading() as load:
            await load.update("Téléchargement de l'image...")
            objet = await self.bot.sget(objet)

            await load.update("Traitement...")
            time_ = time.perf_counter()
            out = await self.bot.in_thread(self.process_ascii, objet, cmap, is_big)
            time_ = time.perf_counter() - time_

            if is_big:
                await load.update("Envoi...")
                url = "https://wastebin.travitia.xyz/"
                try:
                    async with Timeout(3, loop=self.bot.loop):
                        async with self.bot.session.post(url=f"{url}documents", data=out.encode("utf-8")) as p:
                            if p.status == 200:
                                res = await p.json()
                                bin_url = url + res["key"]
                            else:
                                raise asyncio.TimeoutError
                except asyncio.TimeoutError:
                    # Failed..., so we try the others
                    bin_url = await self.bot.safe_bin_post(out)

                await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*\n{bin_url}")
            else:
                await ctx.send(f"*En {round(time_ * 1000, 3)}ms:*")
                await ctx.send(f"```\n{out}\n```")

    @commands.group(name="ascii", invoke_without_command=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art(self, ctx, *, objet: GetImg = None):
        """
        Transforme une image en art ASCII.
        """
        await self.do_ascii_cmd(ctx, objet, 0)

    @ascii_art.command(name="big")
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art_big(self, ctx, *, objet: GetImg = None):
        """
        Fait de même mais en ne changeant pas la taille de l'image.
        """
        await self.do_ascii_cmd(ctx, objet, 0, is_big=True)

    @commands.group(name="ascii2", invoke_without_command=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art2(self, ctx, *, objet: GetImg = None):
        """
        Transforme une image en art ASCII, mais avec moin de details.
        """
        await self.do_ascii_cmd(ctx, objet, 1)

    @ascii_art2.command(name="ascii2")
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art2_big(self, ctx, *, objet: GetImg = None):
        """
        Fait de même mais en ne changeant pas la taille de l'image.
        """
        await self.do_ascii_cmd(ctx, objet, 1, is_big=True)

    @commands.group(name="ascii3", invoke_without_command=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art3(self, ctx, *, objet: GetImg = None):
        """
        Transforme une image en art ASCII, avec les caractères  ░▒▓█.
        """
        await self.do_ascii_cmd(ctx, objet, 2)

    @ascii_art3.command(name="big")
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art3_big(self, ctx, *, objet: GetImg = None):
        """
        Fait de même mais en ne changeant pas la taille de l'image.
        """
        await self.do_ascii_cmd(ctx, objet, 2, is_big=True)

    @commands.group(name="ascii4", invoke_without_command=True)
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art4(self, ctx, *, objet: GetImg = None):
        """
        Transforme une image en art ASCII, avec les caractères  □■.
        """
        await self.do_ascii_cmd(ctx, objet, 3)

    @ascii_art4.command(name="ascii4")
    @commands.cooldown(1, 10, BucketType.user)
    async def ascii_art4_big(self, ctx, *, objet: GetImg = None):
        """
        Fait de même mais en ne changeant pas la taille de l'image.
        """
        await self.do_ascii_cmd(ctx, objet, 3, is_big=True)


def setup(bot):
    bot.add_cog(Images(bot))

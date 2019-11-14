import asyncio
import concurrent.futures
import io
import logging
import os
import socket
import sys
import time
import traceback
from collections import defaultdict
from contextlib import contextmanager, suppress
from datetime import datetime

import aiohttp
import discord
from async_timeout import timeout as Timeout
from discord.ext import commands

from .cogs.utils import BINS, SgetError, context, ctimestamp
from config import BOT_PREFIX, STATUS, TOKEN

try:
    import aiodns
except ImportError:
    aiodns = False

Resolver = aiohttp.AsyncResolver if aiodns else aiohttp.ThreadedResolver

# We set up logging...
@contextmanager
def setup_log():
    try:
        loggers = [
            logging.getLogger("discord"),
            logging.getLogger("discord.http"),
            logging.getLogger("discord.gateway")
        ]
        handler = logging.FileHandler(
            filename="katbot.log",
            encoding="utf-8",
            mode="w"
        )
        fmt = logging.Formatter(
            '[{asctime}] [{levelname:<7}] {name}: {message}',
            datefmt="%d/%m/%Y - %H:%M:%S",
            style="{"
        )
        handler.setFormatter(fmt)
        for log in loggers:
            log.setLevel(logging.WARN)
            log.addHandler(handler)

        yield

    finally:
        for l in loggers:
            for h in l.handlers:
                h.close()
                l.removeHandler(h)


class KatBOT(commands.Bot):
    """
    The bot
    """

    def __init__(self):
        super().__init__(
            command_prefix=self._get_prefix,
            description="Un bot fait par ItsKat#8668",
            connector=aiohttp.TCPConnector(
                resolver=Resolver(),
                family=socket.AF_INET,
                ttl_dns_cache=120
            )
        )
        self.session = None  # Filled in later

        self.snipe_data = {}
        self.seen_messages = 0
        self.command_usage = defaultdict(int)

        self.loading_emotes = [
            "a:katbotloadspin:521005026349547523",
            "a:katbotloadspinfast:521005125536448523",
            "a:katbotloadwrench:521005240854511617",
            "a:katbotloadcycle:521005325940162570",
            "a:katbotloadclock:521005405833265153",
        ]
        self.exit_code = 1

        self.initial_extensions = ["katbot.cogs.listenersloops",
                                   "katbot.cogs.utilites",
                                   "katbot.cogs.owner",
                                   "katbot.cogs.images",
                                   "katbot.cogs.misc",
                                   "katbot.cogs.info",
                                   "katbot.cogs.apis",
                                   "katbot.cogs.errors"]
        self.load_exts()

    def load_exts(self):
        print("Loading cogs...")
        for extension in self.initial_extensions:
            try:
                self.load_extension(extension)
            except Exception:
                print(f'Failed to load: {extension}.', file=sys.stderr)
                traceback.print_exc()
            else:
                print(f"Succesfully loaded {extension}!")
        with suppress(commands.ExtensionNotFound):
            os.environ["JISHAKU_NO_UNDERSCORE"] = "true"
            self.load_extension("jishaku")

        print("Done loading cogs!\n-------\n")

    def _get_prefix(self, bot, message):
        if not message.guild:
            return BOT_PREFIX

        return commands.when_mentioned_or(*[BOT_PREFIX])(bot, message)

    async def process_commands(self, message):
        if message.author.bot:
            return

        ctx = await self.get_context(message, cls=context.Ctx)
        if not ctx.command:
            return
        else:
            await self.invoke(ctx)

    async def on_message(self, message):
        self.seen_messages += 1

        await self.process_commands(message)

    async def on_ready(self):
        if not hasattr(self, "connection_time"):
            self.connection_time = time.time() - self.connection_start
        self.uptime_data = datetime.now()

        print(f"\nLogged in as: {self.user.name} - {self.user.id}")
        print(f"Library version: {discord.__version__}\n")

        await self.change_presence(
            activity=discord.Activity(
                name=STATUS,
                type=discord.ActivityType.watching
            )
        )
        ch = self.get_channel(553597441631322114)
        await ch.send(f"Bot connecté le {ctimestamp()}")

        if os.path.isfile("restart"):
            with open("restart", "r", encoding="utf=8") as f:
                data = f.read().splitlines()
            try:
                await self.http.edit_message(int(data[1]), int(data[0]), content="Fait!")
                os.remove("restart")
            except discord.HTTPException:
                pass

        print("The bot is ready!\n")

    async def start(self, *args, **kwargs):
        await self.create_session()
        await super().start(*args, **kwargs)

    async def close(self):
        await self.session.close()
        await super().close()

    async def create_session(self):
        """
        Creates the http session in a coro, like that aiohttp stops whining
        """
        if isinstance(self.session, aiohttp.ClientSession):
            await self.session.close()
        self.session = aiohttp.ClientSession(
            loop=self.loop,
            cookie_jar=aiohttp.DummyCookieJar(
                loop=self.loop
            ),
            connector=aiohttp.TCPConnector(
                resolver=Resolver(),
                family=socket.AF_INET,
                loop=self.loop
            )
        )

    async def sget(self, url, *, buffer=False, json=None, timeout=2, max_size=3*(10**6), trust_host=False):
        """
        An async function that simplifies the logic of a get method
        """
        try:
            async with Timeout(timeout, loop=self.loop):
                async with self.session.get(url) as r:
                    try:
                        if int(r.headers["Content-Length"]) > max_size:
                            raise SgetError(f"Tentative de téléchargement d'un fichier trop gros.")
                    except KeyError:
                        # Sometimes, Content-Lenght header will be missing.
                        # If we trust the host, we can ignore the max_size...
                        if not trust_host:
                            raise SgetError("Taille du fichier à téléchargement inconue.")

                    if r.status == 200:
                        if json:
                            j = await r.json()
                            return j[json]

                        elif buffer:
                            data = await r.read()
                            return io.BytesIO(data)
                        else:
                            return await r.read()
                    else:
                        raise SgetError(f"Le téléchargement n'a pas abouti (status HTTP: {r.status}).")
        except asyncio.TimeoutError as e:
            raise SgetError("Le téléchargement à pris trop de temps.") from e

    async def safe_bin_post(self, content):
        data = content.encode("utf-8")
        for url in BINS:
            try:
                async with Timeout(2, loop=self.loop):
                    async with self.session.post(url=f"{url}documents", data=data) as p:
                        if p.status == 200:
                            res = await p.json()
                            return url + res["key"]
                        else:
                            continue
            except asyncio.TimeoutError:
                pass
        return None

    async def in_thread(self, func, *args, **kwargs):
        thread = kwargs.pop("thread", True)
        if thread:
            Pool = concurrent.futures.ThreadPoolExecutor
        else:
            Pool = concurrent.futures.ProcessPoolExecutor
        with Pool() as p:
            res = await self.loop.run_in_executor(
                p,
                func,
                *args,
                **kwargs
            )
        return res

    def new_task(self, coro):
        return self.loop.create_task(coro)

    def __call__(self):
        try:
            print("Logging in...")
            self.connection_start = time.time()
            self.run(TOKEN, bot=True, reconnect=True)

        finally:
            sys.exit(self.exit_code)

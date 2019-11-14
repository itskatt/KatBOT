import copy
import glob
import importlib
import io
import random
import textwrap
import time
import traceback
import typing
from contextlib import redirect_stdout
from datetime import datetime

import discord
import import_expression
from discord.ext import commands

from config import STATUS

from .utils import EMBED_COLOUR
from .utils.context import Ctx
from .utils.paginator import TextPages
from .utils.asyncshell import run


class Timer():
    def __enter__(self):
        self._started = time.perf_counter()
        return self

    def __exit__(self, type, value, traceback):
        end = time.perf_counter()
        self.elapsed = end - self._started


CORO_CODE = """\
async def func():
    from importlib import import_module as {0}
    with __timer:
{{0}}
""".format(import_expression.constants.IMPORTER)


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code. Used for eval"""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, cog: str, not_in_cogs=None):
        """Loads a Module."""
        if not not_in_cogs:
            cog = f"cogs.{cog}"

        try:
            self.bot.load_extension(cog)
        except Exception as e:
            await ctx.send(f'Erreur:\n```fix\n{type(e).__name__}: {e}\n```')
            await ctx.tick(False)
        else:
            await ctx.tick()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, cog: str, not_in_cogs=None):
        """Unloads a Module."""
        if not not_in_cogs:
            cog = f"cogs.{cog}"

        try:
            self.bot.unload_extension(cog)
        except Exception as e:
            await ctx.send(f'Erreur:\n```fix\n{type(e).__name__}: {e}\n```')
            await ctx.tick(False)
        else:
            await ctx.tick()

    # Reload
    @commands.command(hidden=True, aliases=["rl"])
    @commands.is_owner()
    async def reload(self, ctx, cog: str, not_in_cogs=None):
        """Reloads a Module."""
        if not not_in_cogs:
            cog = f"cogs.{cog}"

        if cog == "cogs.*":
            fmt = []
            # First we reload submodules (utils)
            sub = [s.replace("\\", "/") for s in glob.glob("cogs/utils/*.py")]
            for s in sub:
                s = s.rpartition("/")[2][:-3]
                if s == "__init__":
                    s = "cogs.utils"
                else:
                    s = f"cogs.utils.{s}"
                importlib.reload(importlib.import_module(s))
            # We can now reload all cogs
            for exts in self.bot.initial_extensions:
                try:
                    self.bot.reload_extension(exts)
                except Exception as e:
                    fmt.append(f'Erreur dans **{exts}**:\n\t```fix\n{type(e).__name__} - {e}\n```')
            if not fmt:
                return await ctx.tick()
        else:
            try:
                self.bot.reload_extension(cog)
            except Exception as e:
                await ctx.send(f'Erreur:\n```fix\n{type(e).__name__} - {e}\n```')
                return await ctx.tick(False)
            else:
                return await ctx.tick()

        await ctx.send("\n".join(fmt))

    # Eval cmd TODO: rework
    @commands.command(name="eval", aliases=["ev"], hidden=True)
    @commands.is_owner()
    async def eval_(self, ctx, *, code):
        rle = random.choice(self.bot.loading_emotes)
        embed = discord.Embed(
            title="En cours...",
            description=f"<{rle}>",
            color=EMBED_COLOUR,
            timestamp=datetime.utcnow()
        )
        message = await ctx.send(embed=embed)

        timer = Timer()

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            "_": self._last_result,
            "__timer": timer
        }

        env.update(globals())

        code = self.cleanup_code(code)
        stdout = io.StringIO()

        to_parse = CORO_CODE.format(textwrap.indent(code, " " * 8))

        try:
            parsed = import_expression.parse(to_parse, mode="exec")
            exec(compile(parsed, "<eval>", "exec"), env)

        except Exception as e:
            embed.title = "Erreur lors de la compilation"
            embed.description = f'```fix\n{e.__class__.__name__}: {e}\n```'
            await message.edit(embed=embed)

            await ctx.tick(False)
            await ctx.add_delete_reaction(message)
            return

        func = env["func"]
        try:
            with redirect_stdout(stdout):
                ret = await func()

        except Exception:
            value = stdout.getvalue()
            embed.title = "Erreur lors de l'éxecution"
            desc = f"{value}{traceback.format_exc()}"

            if len(desc) > 2015:
                desc = desc[:2015] + "..."
            embed.description = f"```py\n{desc}\n```"
            await message.edit(embed=embed)

            await ctx.tick(False)
            await ctx.add_delete_reaction(message)
        else:
            value = stdout.getvalue()
            try:
                await ctx.tick()
            except discord.Forbidden:
                pass

            embed.title = "Succès!"
            embed.description = f"En {round(timer.elapsed, 3)}s"

            if ret is None:
                if value:
                    text = value
                else:
                    await message.edit(embed=embed)
                    await ctx.add_delete_reaction(message)
                    return
            else:
                self._last_result = ret
                text = f"{value}{ret}"

            class EvalPages(TextPages):
                async def stop_pages(self):
                    await message.delete()
                    await super().stop_pages()

            p = EvalPages(
                ctx,
                text,
                prefix="```py",
                suffix="```",
                stop_deletes=True
            )
            await message.edit(embed=embed)
            await p.paginate()

    # Eval cmd error handler
    @eval_.error
    async def on_eval_cmd_error(self, ctx, error):
        if isinstance(error, commands.errors.NotOwner):
            await ctx.send("Tu n'est pas le propriétaire de ce bot.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("code?")
        else:
            message = await ctx.send(
                "__**Erreur:**__\n"
                f"```py\n{traceback.format_exc()}\n```"
            )
            try:
                await ctx.add_delete_reaction(message)
            except discord.Forbidden:
                pass

    @commands.command(hidden=True, aliases=["sh", "bash"])
    @commands.is_owner()
    async def shell(self, ctx, *, code: str):
        async with ctx.typing():
            stdout, stderr, code = await run(code)

            if stderr:
                out = f"stdout:\n{stdout}\nstderr:\n{stderr}\n\nReturn code: {code}"
            else:
                out = stdout
                if not code:
                    out = f"stdout:\n{stdout}\nstderr:\n{stderr}\n\nReturn code: {code}"

        pages = TextPages(ctx, out, stop_deletes=True)
        await pages.paginate()

    @commands.group(name="bot", hidden=True, invoke_without_command=True)
    @commands.is_owner()
    async def _bot(self, ctx):
        await ctx.send_help(ctx.command)

    @_bot.command(aliases=["sn"])
    @commands.is_owner()
    async def setnick(self, ctx, nick: str = None):
        try:
            await ctx.me.edit(nick=nick)
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command()
    @commands.is_owner()
    async def delmsg(self, ctx, msg: int, channel: discord.TextChannel = None):
        try:
            if channel is None:
                channel = ctx.channel

            m = await channel.fetch_message(msg)
            await m.delete()
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command()
    @commands.is_owner()
    async def dm(self, ctx, usr: int, *, txt: str):
        try:
            usr = self.bot.get_user(usr)
            await usr.send(txt)
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command(aliases=["status"])
    @commands.is_owner()
    async def setpresence(self, ctx, *, presence: str = None):
        try:
            if presence is None:
                status = STATUS
            else:
                status = presence
            await self.bot.change_presence(activity=discord.Activity(name=status, type=discord.ActivityType.listening))
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command(aliases=["tell", "echo"])
    @commands.is_owner()
    async def dis(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, msg: str):
        try:
            if channel is None:
                channel = ctx.channel
            await channel.send(msg)
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command(aliases=["menage", "cl"])
    @commands.is_owner()
    async def cleanup(self, ctx, limit: int = 1):
        try:
            perms = ctx.channel.permissions_for(ctx.me).manage_messages

            def me(m):
                return m.author.id == self.bot.user.id
            await ctx.channel.purge(
                limit=limit,
                check=me,
                bulk=perms
            )
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command(aliases=["desactive"])
    @commands.is_owner()
    async def disable(self, ctx, *, command):
        try:
            cmd = self.bot.get_command(command)
            cmd.enabled = False
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    @_bot.command(alias=["active"])
    @commands.is_owner()
    async def enable(self, ctx, *, command):
        try:
            cmd = self.bot.get_command(command)
            cmd.enabled = True
            await ctx.tick()
        except Exception:
            await ctx.tick(False)

    # Logout command
    @commands.command(aliases=["meur", "die"], hidden=True)
    @commands.is_owner()
    async def logout(self, ctx):
        await ctx.send("Au revoir!")
        self.bot.exit_code = 0
        await self.bot.logout()

    @commands.command(aliases=["reboot", "redemare"], hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        m = await ctx.send(f"Redemarage... <{random.choice(self.bot.loading_emotes)}>")
        with open("restart", "w", encoding="utf=8") as f:
            f.write(f"{m.id}\n{m.channel.id}")
        self.bot.exit_code = 1
        await self.bot.logout()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def su(self, ctx, member: typing.Union[discord.Member, discord.User], *, cmd: str):
        msg = copy.copy(ctx.message)
        msg.author = member
        msg.content = ctx.prefix + cmd
        new_ctx = await self.bot.get_context(msg, cls=Ctx)
        await self.bot.invoke(new_ctx)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def sudo(self, ctx, *, cmd: str):
        if cmd == "!!":
            async for m in ctx.history(limit=15):
                if m.author != ctx.author:
                    continue
                if m == ctx.message:  # prevent infinit loop
                    continue
                if m.content.startswith(ctx.prefix):
                    cmd = m.content[len(ctx.prefix):]
                    if cmd.startswith("sudo"):  # same
                        continue
                    await ctx.send(f"sudo **{cmd}**")
                    break

        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + cmd
        new_ctx = await self.bot.get_context(msg, cls=Ctx)
        return await new_ctx.command.reinvoke(new_ctx)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def combo(self, ctx, *, cmds: str):
        """Sep is ` && `"""
        cmds = cmds.split(" && ")
        msg = copy.copy(ctx.message)
        for c in cmds:
            msg.content = ctx.prefix + c
            new_ctx = await self.bot.get_context(msg, cls=Ctx)
            await self.bot.invoke(new_ctx)

    @commands.command(aliases=["newreport", "newrep", "nr"], hidden=True)
    @commands.is_owner()
    async def new_report(self, ctx):
        try:
            c = self.bot.get_cog("ListenersLoops")
            c.do_report.restart()
            await ctx.tick()
        except Exception:
            await ctx.tick(False)


def setup(bot):
    bot.add_cog(Owner(bot))

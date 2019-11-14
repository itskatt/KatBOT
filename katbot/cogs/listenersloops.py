import asyncio
import sys
from datetime import datetime
from textwrap import dedent

import discord
import psutil
from discord.ext import commands, tasks

from config import STATUS

from .utils import EMBED_COLOUR, ctimestamp, gettime


class ListenersLoops(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.do_report.start()  # pylint: disable=no-member
        self.change_presence.start()  # pylint: disable=no-member

    def cog_unload(self):
        self.change_presence.cancel()  # pylint: disable=no-member
        self.do_report.cancel()  # pylint: disable=no-member

    def adjust_val(self, val, index):
        if not self.last_usage:
            return ""

        before = self.last_usage[index]
        if before < val:
            return f"+{round(val - before, 2)}%"

        elif before > val:
            return f"-{round(before - val, 2)}%"

        else:
            return "inchangé"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return

        if isinstance(message.channel, discord.DMChannel):
            ch = self.bot.get_channel(531519876251123743)  # dm
            embed = discord.Embed(color=0x7cdef9, description=str(f"Le {ctimestamp()}"))
            embed.set_author(name=str(message.author), icon_url=message.author.avatar_url)
            embed.set_footer(text=message.content)
            await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.attachments:
            att = message.attachments[0]
            if not att.width:
                att = None
        else:
            att = None
        self.bot.snipe_data[message.channel.id] = {
            "content": message.content,
            "image": att,
            "author": message.author,
            "timestamp": datetime.utcnow()
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content != after.content:
            await self.bot.process_commands(after)

    @commands.Cog.listener()
    async def on_command(self, ctx):
        self.bot.command_usage[ctx.command.qualified_name] += 1

        ch = self.bot.get_channel(534060327395131394)  # commandes
        embed = discord.Embed(
            color=EMBED_COLOUR,
            description=f"Le {ctimestamp()}\n"
                        f"Commande **{ctx.command}** utilisé dans **{ctx.guild}**, salon **{ctx.channel}**."
        )
        embed.set_author(name=str(ctx.message.author), icon_url=ctx.message.author.avatar_url)
        await ch.send(embed=embed)

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        if isinstance(channel, discord.DMChannel) and not user.id == self.bot.user.id:
            await channel.trigger_typing()

    @tasks.loop(hours=1)
    async def change_presence(self):
        await self.bot.change_presence(
            activity=discord.Activity(
                name=STATUS,
                type=discord.ActivityType.watching
            )
        )

    @change_presence.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=1)
    async def do_report(self):
        ram_perc = psutil.virtual_memory().percent
        disk_perc = psutil.disk_usage("C:\\" if sys.platform == "win32" else "/").percent
        cpu_perc = psutil.cpu_percent()

        if not hasattr(self, "last_usage"):
            self.last_usage = ()

        fmt = dedent("""\
        **---**
        Rapport effectué le **{date_raport}**.
        Bot en ligne depuis le **{uptime_bot}**,
        soit **{uptime_bot_2}**.
        ```
         RAM: {ram}% | {diff_ram}
        DISK: {disk}% | {diff_disk}
         CPU: {cpu}%  | {diff_cpu}
        ```
        """)

        fmt = fmt.format(
            date_raport=ctimestamp(),
            uptime_bot=self.bot.uptime_data.strftime('%d/%m/%Y à %H:%M'),
            uptime_bot_2=gettime((datetime.now() - self.bot.uptime_data).seconds),

            ram=ram_perc,
            disk=disk_perc,
            cpu=cpu_perc,

            diff_ram=self.adjust_val(ram_perc, 0),
            diff_disk=self.adjust_val(disk_perc, 1),
            diff_cpu=self.adjust_val(cpu_perc, 2)
        )

        self.last_usage = (ram_perc, disk_perc, cpu_perc)

        ch = self.bot.get_channel(553598587611774986)  # raports
        await ch.send(fmt)

    @do_report.before_loop
    async def before_report(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)


def setup(bot):
    bot.add_cog(ListenersLoops(bot))

import itertools
import time
from datetime import datetime

import discord
import psutil
from discord.ext import commands

from .utils import EMBED_COLOUR, gettime
from .utils.asyncshell import get_temp, get_linecount
from .utils.paginator import HelpPaginator


class PaginatedHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(command_attrs={
            "cooldown": commands.Cooldown(1, 3, commands.BucketType.member),
            "help": "Pour obtenir de l'aide, a propos d'une commande, catégorie ou du bot.",
            "aliases": ["h", "aide"]
        })

    def get_command_signature(self, command):
        parent = command.full_parent_name
        if len(command.aliases) > 0:
            aliases = '|'.join(command.aliases)
            fmt = f'[{command.name}|{aliases}]'
            if parent:
                fmt = f'{parent} {fmt}'
            alias = fmt
        else:
            alias = command.name if not parent else f'{parent} {command.name}'
        return f'{alias} {command.signature}'

    async def send_bot_help(self, mapping):
        def key(c):
            return c.cog_name or '\u200bSans catégorie'

        bot = self.context.bot
        entries = await self.filter_commands(bot.commands, sort=True, key=key)
        nested_pages = []
        per_page = 9
        total = 0

        for cog, commands_ in itertools.groupby(entries, key=key):
            commands_ = sorted(commands_, key=lambda c: c.name)
            if len(commands_) == 0:
                continue

            total += len(commands_)
            actual_cog = bot.get_cog(cog)
            # get the description if it exists (and the cog is valid) or return Empty embed.
            description = (actual_cog and actual_cog.description) or discord.Embed.Empty
            nested_pages.extend((cog, description, commands_[i:i + per_page])
                                for i in range(0, len(commands_), per_page))

        # a value of 1 forces the pagination session
        pages = HelpPaginator(self, self.context, nested_pages, per_page=1)

        # swap the get_page implementation to work with our nested pages.
        pages.get_page = pages.get_bot_page
        pages.is_bot = True
        pages.total = total
        await pages.paginate()

    async def send_cog_help(self, cog):
        entries = await self.filter_commands(cog.get_commands(), sort=True)
        pages = HelpPaginator(self, self.context, entries)
        pages.title = cog.qualified_name
        pages.description = cog.description

        await pages.paginate()

    def common_command_formatting(self, page_or_embed, command):
        page_or_embed.title = self.get_command_signature(command)
        if command.description:
            page_or_embed.description = f'{command.description}\n\n{command.help}'
        else:
            page_or_embed.description = command.help or "Pas d'aide précisée."

    async def send_command_help(self, command):
        # No pagination necessary for a single command.
        embed = discord.Embed(colour=EMBED_COLOUR)
        self.common_command_formatting(embed, command)
        await self.context.send(embed=embed)

    async def send_group_help(self, group):
        subcommands = group.commands
        if len(subcommands) == 0:
            return await self.send_command_help(group)

        entries = await self.filter_commands(subcommands, sort=True)
        pages = HelpPaginator(self, self.context, entries)
        self.common_command_formatting(pages, group)

        await pages.paginate()

    def command_not_found(self, string):
        return f"\"{string}\" n'est pas une commande ou catégorie de ce bot."

    def subcommand_not_found(self, command, string):
        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return f"La commande \"{command.qualified_name}\" n'a pas de sous-commande appelé {string}"
        return f"La commande \"{command.qualified_name}\" n'a pas de sous-commandes."


class Infos(commands.Cog):
    """
    Commandes pour obtenir des informations et de l'aide sur le bot.
    """

    def __init__(self, bot):
        self.bot = bot
        self.old_help_command = self.bot.help_command
        bot.help_command = PaginatedHelpCommand()
        bot.help_command.cog = self

    def cog_unload(self):
        self.bot.help_command = self.old_help_command

    # @commands.command(aliases=["i"])
    # @commands.cooldown(1, 10, commands.BucketType.channel)
    # async def info(self, ctx):
        # """
        # Donne quelques infos sur le bot.
        # Ce sont l'uptime du serveur, temprature,
        # utilisation du CPU, et d'autres...
        # """

    #     await ctx.trigger_typing()
    #     mem = psutil.virtual_memory()
    #     mem = {
    #         "Total": f"{round(mem.total / (1024 * 1024), 1)} MB",
    #         "Utilisé": f"{round(mem.used / (1024 * 1024), 1)} MB",
    #         "Disponible": f"{round(mem.free / (1024 * 1024), 1)} MB",
    #         "Pourcentage": f"{round(mem.percent, 1)} %"
    #     }
    #     disk = psutil.disk_usage("C:\\" if sys.platform == "win32" else "/")
    #     disk = {
    #         "Total": f"{round(disk.total / (1024 * 1024) / 1000, 1)} GB",
    #         "Utilisé": f"{round(disk.used / (1024 * 1024) / 1000, 1)} GB",
    #         "Disponible": f"{round(disk.free / (1024 * 1024) / 1000, 1)} GB",
    #         "Pourcentage": f"{round(disk.percent, 1)} %"
    #     }

    #     embed = discord.Embed(color=0x7cdef9)
    #     embed.set_author(name=f"{self.bot.user.name} - Info",
    #                      icon_url=self.bot.user.avatar_url)
    #     # Server uptime
    #     embed.add_field(name="**Uptime du serveur**",
    #                     value=get_uptime(),
    #                     inline=False)
    #     # Bot uptime
    #     embed.add_field(name="**Uptime du bot**",
    #                     value=gettime((datetime.now() - self.bot.uptime_data).seconds),
    #                     inline=False)
    #     # CPU temperature
    #     embed.add_field(name="**Temperature du CPU**",
    #                     value=await get_temp(),
    #                     inline=False)
    #     # CPU usage
    #     embed.add_field(name="**Utilisation du CPU (%)**",
    #                     value=str(psutil.cpu_percent()),
    #                     inline=False)
    #     # Ram usage/info
    #     embed.add_field(name="**Utilisation de la RAM**",
    #                     value="\n".join([f"{key}: {mem[key]}" for key in mem]),
    #                     inline=False)
    #     # Disk usage/info
    #     embed.add_field(name="**Utilisation du stockage**",
    #                     value="\n".join(
    #                         [f"{key}: {disk[key]}" for key in mem]),
    #                     inline=False)
    #     # Bot connection time
    #     embed.add_field(name="**Temps de connection a l'API (S)**",
    #                     value=round(self.bot.connection_time, 3),
    #                     inline=False)

    #     await ctx.send(
    #         content=f"{self.bot.user.name} est un simple bot discord créé pour le fun par **ItsKat#8668**.\n"
    #                 "Voici quelques informations à propos du bot:",
    #         embed=embed
    #     )

    @commands.command(aliases=["i"])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def info(self, ctx):
        """
        Donne quelques infos sur le bot.
        """
        async with ctx.typing():
            # TODO: better look,...
            # Getting info...
            mem = psutil.virtual_memory()
            mem = (
                round(mem.total / (1024 * 1024), 1),
                round(mem.used / (1024 * 1024), 1),
                round(mem.percent, 1)
            )
            cmds = sum([self.bot.command_usage[u] for u in self.bot.command_usage])
            # The actual embed
            embed = discord.Embed(
                color=EMBED_COLOUR,
                description=f"Un simple bot Discord créé par **ItsKat#8668**.",
                timestamp=datetime.utcnow()
            )
            embed.set_author(
                name=str(self.bot.user),
                icon_url=str(self.bot.user.avatar_url_as(format="png", size=16))
            )

            embed.add_field(
                name="Uptimes",
                value=f"Serveur: {gettime(time.time() - psutil.boot_time())}\n"
                      f"Bot: {gettime((datetime.now() - self.bot.uptime_data).seconds)}",
                inline=False
            )
            embed.add_field(
                name="CPU",
                value=f"Utilisation: `{psutil.cpu_percent()}%`\n"
                      f"Temperature: `{await get_temp()}`"
            )
            embed.add_field(
                name="RAM",
                value=f"Utilisation: `{mem[1]}MB/{mem[0]}MB`\n"
                      f"Pourcentage: `{mem[2]}%`"
            )
            embed.add_field(
                name="Stats",
                value=f"Messages vus par le bot: `{self.bot.seen_messages}`\n"
                      f"Commandes utilisées: `{cmds}`"
            )
            embed.add_field(
                name="Lignes de code",
                value=await get_linecount()
            )
            embed.add_field(
                name="Temps de préparation",
                value=f"{self.bot.connection_time:.3f}s"
            )
            await ctx.send(embed=embed)

    # Ping command
    @commands.command(aliases=["p"])
    async def ping(self, ctx):
        """
        Donne la latence du bot a l'API de Discord.
        """
        start_typing = time.perf_counter()
        await ctx.trigger_typing()
        end_typing = time.perf_counter()
        duration_typing = (end_typing - start_typing) * 1000

        start = time.perf_counter()
        message = await ctx.send('Une seconde...')
        end = time.perf_counter()
        duration = (end - start) * 1000

        lat = self.bot.latency
        lat = lat * 1000

        avg = (duration_typing + duration + lat) / 3

        await message.edit(
            content=(
                "Pong!\n**`typing`:** {:.2f}ms\n**`message`:** {:.2f}ms\n**`latency`:** {:.2f}ms\n**`avg`:** {:.2f}ms"
                .format(duration_typing, duration, lat, avg)
            )
        )


def setup(bot):
    bot.add_cog(Infos(bot))

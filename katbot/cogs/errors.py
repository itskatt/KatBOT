import sys
import traceback

import discord
from discord.ext import commands

from .utils import convs, ctimestamp, SgetError


class ErrorHandlers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def arg_fmt(self, arg: str):
        """Formats an argument by removing arg~~:foo..~~"""
        if ":" in arg:
            return arg.split(":")[0]
        else:
            return arg

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        if hasattr(ctx.command, 'on_error') and not hasattr(error, "force__"):
            return

        ignored = (commands.CommandNotFound, commands.CommandInvokeError)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored):
            return

        elif isinstance(error, commands.DisabledCommand):
            return await ctx.send(f'La commande **{ctx.command}** a été désactivée')

        elif isinstance(error, commands.CommandOnCooldown):
            seconds = error.retry_after
            seconds = round(seconds, 2)
            return await ctx.send(f'*Vous pouriez reutilisez cette commande dans **{seconds}** secondes.*')

        elif isinstance(error, commands.NotOwner):
            return await ctx.send("Tu n'est pas le proprietaire de ce bot.")

        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(error.missing_perms)
            return await ctx.send(
                f"Vous ne pouvez pas executer la commande **{ctx.command}**;"
                f"il vous manque la/les permition(s) suivante(s):\n{perms}"
            )

        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(error.missing_perms)
            return await ctx.send(
                "Je suis désolé, mais je n'ai pas pu executer votre demande.\n"
                f"Il me manque la/les permition(s) suivante(s) pour executer la commande **{ctx.command}**:\n{perms}\n"
                "*Veuilez contactez un administrateur du serveur.*"
            )

        elif isinstance(error, commands.NoPrivateMessage):
            try:
                return await ctx.author.send(
                    f'Desolé, mais **{ctx.command}** ne peut pas etre utilisée en messages privés.'
                )
            except discord.Forbidden:
                return

        elif isinstance(error, commands.MissingRequiredArgument):
            return await ctx.send(f"Argument **{self.arg_fmt(str(error.param))}** requis...")

        elif isinstance(error, commands.TooManyArguments):
            return await ctx.send("Trops d'arguments on été passé...")

        elif isinstance(error, discord.Forbidden):
            return await ctx.send(
                "Je suis désolé, mais je n'ai pas pu executer votre demande.\n"
                "Il me manque des permitions pour éxécuter cette commande.\n"
                "*Veuilez contactez un administrateur du serveur.*"
            )

        elif isinstance(error, SgetError):
            await ctx.send(error)

        elif isinstance(error, convs.MemberConvFail):
            m = error.member
            return await ctx.send(f"*{m}* n'existe pas comme membre de ce serveur...")

        elif isinstance(error, convs.UserConvFail):
            u = error.user
            return await ctx.send(f"Je n'ai pas pu trouver *{u}* comme utilisateur discord...")

        elif isinstance(error, convs.ImageNotFound):
            return await ctx.send("Je n'ai pas pus trouver une image. Désolé(e)...")

        elif isinstance(error, commands.BadArgument):
            return await ctx.send(
                "Erreur au niveaux d'un des arguments. Veuillez verifier par exemple si vous avez accidentelement"
                "rentré du texte au lieu d'un nombre."
            )

        # Unhandled errors
        print(f'Ignoring exception in command {ctx.command}:', file=sys.stderr)
        tb = traceback.format_exception(type(error), error, error.__traceback__)
        tb = "".join(tb)

        print(tb, file=sys.stderr)

        c = self.bot.get_channel(id=519162690514583585)

        if len(tb) > 1950:
            tb = f"{tb[:1950]}\nTronqué..."

        await c.send(
            f"**__-------__**\nLe **{ctimestamp()}**, dans le serveur **{ctx.guild}**, salon **#{ctx.channel}**"
            f":\nCommande **{ctx.command}**:\n ```py\n{tb}\n```\nLien au message ayant causé l'erreur: "
            f"<{ctx.message.jump_url}>\n**__-------__**"
        )

        await ctx.send(
            "Une erreur est survenue...\n"
            f"```fix\n{error.__class__.__name__}: {error}\n```\n"
            "Ne vous inquietez pas, elle a été reportée!"
        )


def setup(bot):
    bot.add_cog(ErrorHandlers(bot))

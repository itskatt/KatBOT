import datetime

import discord
from discord.ext import commands

from .utils import EMBED_COLOUR, gettime
from .utils.convs import MemberConv, UnionMemberUser


class Utilites(commands.Cog, name="Utilitées"):
    """
    Des commandes d'utilitées.
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["joined"])
    @commands.guild_only()
    async def rejoind(self, ctx, *, membre: MemberConv = None):
        """
        Dit quand un membre a rejoind le serveur.
        """
        membre = membre or ctx.author

        delta = (datetime.datetime.now() - membre.joined_at).total_seconds()
        await ctx.send(
            f"{membre.display_name} à rejoind le {membre.joined_at.strftime('%d/%m/%Y at %H:%M')} "
            f"(il y a {gettime(delta)})"
        )

    @commands.command(name='perms', aliases=['permissions'])
    @commands.guild_only()
    async def check_permissions(self, ctx, *, membre: MemberConv = None):
        """
        Une simple commande qui donne les permissions pour un membre.
        """

        membre = membre or ctx.author

        perms = '\n'.join(
            perm for perm, value in membre.guild_permissions if value
        )
        embed = discord.Embed(
            title='Permissions pour:',
            description=ctx.guild.name,
            colour=membre.colour
        )
        embed.set_author(
            icon_url=membre.avatar_url,
            name=str(membre)
        )
        embed.add_field(name='\uFEFF', value=perms)

        await ctx.send(embed=embed)

    @commands.command()
    async def userinfo(self, ctx, utilisateur: UnionMemberUser = None):
        """
        Donne des informations sur un membre de ce serveur ou un utilisateur Discord.
        """

        ut = utilisateur or ctx.author

        embed = discord.Embed(colour=EMBED_COLOUR)
        embed.set_author(name=str(ut))
        embed.set_thumbnail(url=ut.avatar_url)

        compte = []
        compte.append(f"**Nom:** {ut.name}")
        compte.append(f"**Discrimiateur**: {ut.discriminator}")
        compte.append(f"**Id:** {ut.id}")

        age = (datetime.datetime.now() - ut.created_at).total_seconds()
        age = gettime(age)
        crea = (ut.created_at).strftime(f"%d/%m/%Y à %H:%M")

        compte.append(f"**Creation du compte:** Le {crea} ({age})")
        compte.append(
            "**Est un bot**" if ut.bot else "**N'est pas un bot**"
        )

        if isinstance(ut, discord.Member):
            serv = []
            age = (datetime.datetime.now() -
                   ut.joined_at).total_seconds()
            age = gettime(age)
            rejoind = (ut.joined_at).strftime(f"%d/%m/%Y à %H:%M")

            serv.append(f"**A rejoind le serveur:** Le {rejoind} ({age})")

            compte.append(
                "**Est sur mobile**" if ut.is_on_mobile()
                else "**Est sur pc**"
            )

            roles = [r.mention for r in ut.roles if not r == ctx.guild.default_role]
            if roles:
                serv.append(f"**Roles:** {len(roles)} ({', '.join(roles)})")
                serv.append(f"**Top role:** {ut.top_role.mention}")

        embed.add_field(
            name="Compte",
            value="\n".join(compte)
        )
        if isinstance(ut, discord.Member):
            embed.add_field(
                name="Serveur",
                value="\n".join(serv)
            )

        await ctx.send(
            f"Voici ce que j'ai pus trouver sur **{ut}**:",
            embed=embed
        )

    @commands.command(aliases=["avy"])
    async def avatar(self, ctx, utilisateur: UnionMemberUser = None):
        """
        Montre l'avatar d'un membre du serveur ou d'un utilisateur Discord.
        """
        ut = utilisateur or ctx.author

        fmt = "gif" if ut.is_avatar_animated() else "png"
        main_avy = str(ut.avatar_url_as(format=fmt))

        embed = discord.Embed(
            title=f"L'avatar de {ut}",
            color=EMBED_COLOUR,
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_image(url=main_avy)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Utilites(bot))

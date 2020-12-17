import functools
import io
import discord
from discord.ext import commands, tasks
from discord.ext.commands.cooldowns import BucketType
import random
from disrank.generator import Generator
import asyncio
import operator

class RanksPlugin(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Client = bot
        self.db = bot.plugin_db.get_partition(self)
        self.active_Ranks = {}

    @commands.Cog.listener()
    async def on_message(self, message):
        print(message.content)

    @commands.command()
    async def say(self, ctx, *, message):
        await ctx.send(message)


def setup(bot):
    bot.add_cog(RanksPlugin(bot))
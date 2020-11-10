import json
from typing import Any, Dict, Union

import discord
from datetime import datetime
from discord.ext import commands

from core import checks
from core.models import PermissionLevel
from .models import apply_vars, SafeString


class TagsPlugin(commands.Cog):
    def __init__(self, bot: modmail) -> none:
        self.bot: discord.Client = bot
        self.db = bot.plugin_db.get_partition(self)

    def apply_vars_dict(self, member, message, invite):
        for k, v in message.items():
            if isinstance(v, dict):
                message[k] = self.apply_vars_dict(member, v, invite)
            elif isinstance(v, str):
                message[k] = apply_vars(self, member, v, invite)
            elif isinstance(v, list):
                message[k] = [self.apply_vars_dict(member, _v, invite) for _v in v]
            if k == 'timestamp':
                message[k] = v[:-1]
        return message

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def tags(self, ctx: commands.Context):
        """
        Create Edit & Manage Tags
        """
        await ctx.send_help(ctx.command)

    @tag.command()
    async def create(self, ctx: commands.Context, name: str, *, value: commands.clean_content) -> None:
        """Create tags for your server.
        Example: tag create hello Hi! I am the bot responding!
        Complex usage: https://github.com/fourjr/rainbot/wiki/Tags
        """
        if value.startswith('http'):
            if value.startswith('https://hasteb.in') and 'raw' not in value:
                value = 'https://hasteb.in/raw/' + value[18:]

            async with self.bot.session.get(value) as resp:
                value = await resp.text()

        if name in [i.qualified_name for i in self.bot.commands]:
            await ctx.send('Name is already a pre-existing bot command')
        else:
            await self.bot.db.update_guild_config(ctx.guild.id, {'$push': {'tags': {'name': name, 'value': value}}})
            await ctx.send(self.bot.accept)

    @tag.command()
    async def remove(self, ctx: commands.Context, name: str) -> None:
        """Removes a tag"""
        await self.bot.db.update_guild_config(ctx.guild.id, {'$pull': {'tags': {'name': name}}})

        await ctx.send(self.bot.accept)

    @tag.command(6, name='list')
    async def list_(self, ctx: commands.Context) -> None:
        """Lists all tags"""
        guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
        tags = [i.name for i in guild_config.tags]

        if tags:
            await ctx.send('Tags: ' + ', '.join(tags))
        else:
            await ctx.send('No tags saved')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if not message.author.bot and message.guild:
            ctx = await self.bot.get_context(message)
            guild_config = await self.bot.db.get_guild_config(ctx.guild.id)
            tags = [i.name for i in guild_config.tags]

            if ctx.invoked_with in tags:
                tag = guild_config.tags.get_kv('name', ctx.invoked_with)
                await ctx.send(**self.format_message(tag.value, message))

    def apply_vars_dict(self, tag: Dict[str, Union[Any]], message: discord.Message) -> Dict[str, Union[Any]]:
        for k, v in tag.items():
            if isinstance(v, dict):
                tag[k] = self.apply_vars_dict(v, message)
            elif isinstance(v, str):
                tag[k] = apply_vars(self.bot, v, message)
            elif isinstance(v, list):
                tag[k] = [self.apply_vars_dict(_v, message) for _v in v]
            if k == 'timestamp':
                tag[k] = v[:-1]
        return tag

    def format_message(self, tag: str, message: discord.Message) -> Dict[str, Union[Any]]:
        updated_tag: Dict[str, Union[Any]]
        try:
            updated_tag = json.loads(tag)
        except json.JSONDecodeError:
            # message is not embed
            tag = apply_vars(self.bot, tag, message)
            updated_tag = {'content': tag}
        else:
            # message is embed
            updated_tag = self.apply_vars_dict(updated_tag, message)

            if 'embed' in updated_tag:
                updated_tag['embed'] = discord.Embed.from_dict(updated_tag['embed'])
            else:
                updated_tag = None
        return updated_tag
    
def setup(bot: modmail) -> None:
    bot.add_cog(Tags(bot))

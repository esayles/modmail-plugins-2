import json

import discord
from datetime import datetime
from discord.ext import commands

from core import checks
from core.models import PermissionLevel
from .models import apply_vars, SafeString


class TagsPlugin(commands.Cog):
    def __init__(self, bot):
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

    def format_message(self, member, message, invite):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            # message is not embed
            message = apply_vars(self, member, message, invite)
            message = {'content': message}
        else:
            # message is embed
            message = self.apply_vars_dict(member, message, invite)

            if any(i in message for i in ('embed', 'content')):
                message['embed'] = discord.Embed.from_dict(message['embed'])
            else:
                message = None
        return message
        
    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def tags(self, ctx: commands.Context):
        """
        Create Edit & Manage Tags
        """
        await ctx.send_help(ctx.command)

    @tags.command()
    async def add(self, ctx: commands.Context, name: str, *, content: str):
        """
        Make a new tag
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
            
    @tags.command()
    async def edit(self, ctx: commands.Context, name: str, *, content: str):
        """
        Edit an existing tag
        Only owner of tag or user with Manage Server permissions can use this command
        """
        tag = await self.find_db(name=name)

        if tag is None:
            await ctx.send(f":x: | Tag with name `{name}` dose'nt exist")
            return
        else:
            member: discord.Member = ctx.author
            if ctx.author.id == tag["author"] or member.guild_permissions.manage_guild:
                await self.db.find_one_and_update(
                    {"name": name},
                    {"$set": {"content": content, "updatedAt": datetime.utcnow()}},
                )

                await ctx.send(
                    f":white_check_mark: | Tag `{name}` is updated successfully!"
                )
            else:
                await ctx.send("You don't have enough permissions to edit that tag")

    @tags.command()
    async def delete(self, ctx: commands.Context, name: str):
        """
        Delete a tag.
        Only owner of tag or user with Manage Server permissions can use this command
        """
        tag = await self.find_db(name=name)
        if tag is None:
            await ctx.send(":x: | Tag `{name}` not found in the database.")
        else:
            if (
                ctx.author.id == tag["author"]
                or ctx.author.guild_permissions.manage_guild
            ):
                await self.db.delete_one({"name": name})

                await ctx.send(
                    f":white_check_mark: | Tag `{name}` has been deleted successfully!"
                )
            else:
                await ctx.send("You don't have enough permissions to delete that tag")

    @tags.command()
    async def claim(self, ctx: commands.Context, name: str):
        """
        Claim a tag if the user has left the server
        """
        tag = await self.find_db(name=name)

        if tag is None:
            await ctx.send(":x: | Tag `{name}` not found.")
        else:
            member = await ctx.guild.get_member(tag["author"])
            if member is not None:
                await ctx.send(
                    f":x: | The owner of the tag is still in the server `{member.name}#{member.discriminator}`"
                )
                return
            else:
                await self.db.find_one_and_update(
                    {"name": name},
                    {"$set": {"author": ctx.author.id, "updatedAt": datetime.utcnow()}},
                )

                await ctx.send(
                    f":white_check_mark: | Tag `{name}` is now owned by `{ctx.author.name}#{ctx.author.discriminator}`"
                )

    @tags.command()
    async def info(self, ctx: commands.Context, name: str):
        """
        Get info on a tag
        """
        tag = await self.find_db(name=name)

        if tag is None:
            await ctx.send(":x: | Tag `{name}` not found.")
        else:
            user: discord.User = await self.bot.fetch_user(tag["author"])
            embed = discord.Embed()
            embed.colour = discord.Colour.green()
            embed.title = f"{name}'s Info"
            embed.add_field(
                name="Created By", value=f"{user.name}#{user.discriminator}"
            )
            embed.add_field(name="Created At", value=tag["createdAt"])
            embed.add_field(
                name="Last Modified At", value=tag["updatedAt"], inline=False
            )
            embed.add_field(name="Uses", value=tag["uses"], inline=False)
            await ctx.send(embed=embed)
            return

    @commands.command()
    async def tag(self, ctx: commands.Context, name: str):
        
        """
        Use a tag!
        """
        tag = await self.find_db(name=name)
        if tag is None:
            await ctx.send(f":x: | Tag {name} not found.")
            return
        else:
            await ctx.send(tag["content"])
            await self.db.find_one_and_update(
                {"name": name}, {"$set": {"uses": tag["uses"] + 1}}
            )
            return

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not msg.content.startswith(self.bot.prefix) or msg.author.bot:
            return
        
        content = msg.content.replace(self.bot.prefix, "")
        names = content.split(" ")

        tag = await self.db.find_one({"name": names[0]})
        thing = json.loads(tag["content"])
        embed = discord.Embed.from_dict(thing['embed'])
        if tag is None:
            return
        else:
            
            
            
            await msg.channel.send(embed=embed)
            await self.db.find_one_and_update(
                {"name": names[0]}, {"$set": {"uses": tag["uses"] + 1}}
            )
            return

    async def find_db(self, name: str):
        return await self.db.find_one({"name": name})
    
def setup(bot):
    bot.add_cog(TagsPlugin(bot))

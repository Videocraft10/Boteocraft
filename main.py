import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Startup event
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    print('Boteocraft initialized')
    print('------')

# Member join event
@bot.event
async def on_member_join(member):
    guild_name = member.guild.name
    await member.send(f'Welcome to {guild_name}, {member.name}!')

# Hello Message event
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!test'):
        await message.channel.send(f'testing {message.author.mention}!')

    # Process commands if any
    await bot.process_commands(message)

# Another test command
@bot.command()
async def test(ctx):
    await ctx.send(f'testing command {ctx.author.mention}!')

from typing import Optional

# Command to assign roles
@bot.command()
@commands.has_permissions(manage_roles=True)
async def assign(ctx, member: Optional[discord.Member] = None, *, role: Optional[str] = None):
    if member is None:
        member = ctx.author

    if role is None:
        await ctx.send('Please specify a role.')
        return

    # Find the role by case-insensitive name match
    found_role = discord.utils.find(lambda r: r.name and r.name.lower() == role.lower(), ctx.guild.roles)
    if found_role is None:
        await ctx.send('Role not found.')
        return

    # Check if the bot's top role is higher than the role to assign
    if found_role >= ctx.guild.me.top_role:
        await ctx.send("I can't assign a role higher or equal to my top role.")
        return
    try:
        await member.add_roles(found_role)
        await ctx.send(f'Assigned {found_role.name} role to {member.mention}.')
    except discord.Forbidden:
        await ctx.send("I don't have permission to assign that role.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

# Command to remove roles
@bot.command()
@commands.has_permissions(manage_roles=True)
async def remove(ctx, member: Optional[discord.Member] = None, *, role: Optional[str] = None):
    if member is None:
        member = ctx.author

    if role is None:
        await ctx.send('Please specify a role.')
        return

    # Find the role by case-insensitive name match
    found_role = discord.utils.find(lambda r: r.name and r.name.lower() == role.lower(), ctx.guild.roles)
    if found_role is None:
        await ctx.send('Role not found.')
        return

    # Check if the bot's top role is higher than the role to remove
    if found_role >= ctx.guild.me.top_role:
        await ctx.send("I can't remove a role higher or equal to my top role.")
        return
    try:
        await member.remove_roles(found_role)
        await ctx.send(f'Removed {found_role.name} role from {member.mention}.')
    except discord.Forbidden:
        await ctx.send("I don't have permission to remove that role.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
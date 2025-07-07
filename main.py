import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
from typing import Optional

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
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print('------')

# Member join event
@bot.event
async def on_member_join(member):
    guild_name = member.guild.name
    await member.send(f'Welcome to {guild_name}, {member.name}!')
    await member.send("Please make sure to read the [*rules!*](https://discord.com/channels/819245576381136896/834514725273993236)")

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

# Custom check to ensure user has a role higher than bot's top role
def has_higher_role_than_bot():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        
        # Get the bot's highest role
        bot_top_role = ctx.guild.me.top_role
        
        # Get the user's highest role
        user_top_role = ctx.author.top_role
        
        # Check if user's top role is higher than bot's top role
        if user_top_role <= bot_top_role:
            try:
                await ctx.author.send("You do not have permission to use this command.")
            except discord.Forbidden:
                # If DM fails, send a message that deletes after 5 seconds
                await ctx.send("You do not have permission to use this command.", delete_after=5)
            return False
        
        return True
    
    return commands.check(predicate)

# Command to assign roles
@bot.command()
@commands.has_permissions(manage_roles=True)
@has_higher_role_than_bot()
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
@has_higher_role_than_bot()
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

# Slash command to assign roles
@bot.tree.command(name="assign", description="Assign a role to a member")
@app_commands.describe(member="The member to assign the role to (defaults to yourself)", role="The role to assign")
async def assign_slash(interaction: discord.Interaction, role: discord.Role, member: Optional[discord.Member] = None):

    # Check if user has manage_roles permission
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You need the 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    # Check if user's top role is higher than bot's top role
    bot_top_role = interaction.guild.me.top_role
    user_top_role = interaction.user.top_role
    
    if user_top_role <= bot_top_role:
        await interaction.response.send_message("You need a role higher than my highest role to use this command.", ephemeral=True)
        return
    
    if member is None:
        member = interaction.user

    # Check if the bot's top role is higher than the role to assign
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I can't assign a role higher or equal to my top role.", ephemeral=True)
        return
    
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f'Assigned {role.name} role to {member.mention}.')
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to assign that role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# Slash command to remove roles
@bot.tree.command(name="remove", description="Remove a role from a member")
@app_commands.describe(member="The member to remove the role from (defaults to yourself)", role="The role to remove")
async def remove_slash(interaction: discord.Interaction, role: discord.Role, member: Optional[discord.Member] = None):
    # Check if user has manage_roles permission
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You need the 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    # Check if user's top role is higher than bot's top role
    bot_top_role = interaction.guild.me.top_role
    user_top_role = interaction.user.top_role
    
    if user_top_role <= bot_top_role:
        await interaction.response.send_message("You need a role higher than my highest role to use this command.", ephemeral=True)
        return
    
    if member is None:
        member = interaction.user

    # Check if the bot's top role is higher than the role to remove
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("I can't remove a role higher or equal to my top role.", ephemeral=True)
        return
    
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f'Removed {role.name} role from {member.mention}.')
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to remove that role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)



bot.run(token, log_handler=handler, log_level=logging.DEBUG)
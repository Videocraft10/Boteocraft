import discord
from discord.ext import commands
from discord import app_commands
import logging
from dotenv import load_dotenv
import os
from typing import Optional
from googleapiclient.discovery import build
from discord.ext import tasks
import datetime

# Setup
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
yt_api = os.getenv('YOUTUBE_API_KEY')
yt_id = os.getenv('YOUTUBE_CHANNEL_ID')
dc_id = os.getenv('DISCORD_CHANNEL_ID')

# -- YT API Setup --
try:
    youtube = build('youtube', 'v3', developerKey=yt_api)
    print("YouTube API initialized successfully.")
except Exception as e:
    print(f"Failed to initialize YouTube API: {e}")
    print("YouTube Bot features will not work")
    
last_video_id = None
next_check_time = None

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

notif_role = os.getenv('NOTIFICATION_ROLE_ID')

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
    if not check_new_youtube_video.is_running():
        check_new_youtube_video.start()
    if not countdown_display.is_running():
        countdown_display.start()


# YouTube video check loop
# This function checks for new videos on the specified YouTube channel
@tasks.loop(seconds=60)  # Check every 60 seconds
async def check_new_youtube_video():
    global last_video_id, next_check_time
    
    # Update next check time
    next_check_time = datetime.datetime.now() + datetime.timedelta(seconds=60)
    
    print("\nChecking for new YouTube videos...")

    try:
        # Request "uploads" playlist of set channel
        channel_request = youtube.channels().list(
            part='contentDetails',
            id=yt_id
        )
        channel_response = channel_request.execute()

        # Get the uploads playlist ID
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Request lastest video in the uploads playlist
        playlsit_request = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_playlist_id,
            maxResults=1 # Get only the latest video
        )

        playlist_response = playlsit_request.execute()

        if not playlist_response['items']:
            print("No videos found in the uploads playlist.")
            return
        
        # Get the latest video details
        latest_video = playlist_response['items'][0]
        latest_video_id = latest_video['snippet']['resourceId']['videoId']
        latest_video_title = latest_video['snippet']['title']

        # Check if this is the first time running the check
        if last_video_id is None:
            # Since this is the first run, store the latest video ID and dont post anything
            last_video_id = latest_video_id
            print(f"First run, setting last_video_id to {last_video_id}")
            return
        
        # If the last video ID is different from the latest video ID, its a new vid!
        if last_video_id != latest_video_id:
            print(f"New video found: {latest_video_title} (ID: {latest_video_id})")
            last_video_id = latest_video_id #update the last video ID to the latest one

            # Create YouTube video link
            video_url = f'https://www.youtube.com/watch?v={latest_video_id}'

            # Get the Discord channel to send the message
            notification_channel = bot.get_channel(int(dc_id))
             
            if notification_channel:
                if notif_role == 'everyone':
                    # Send the message to the channel
                    await notification_channel.send(f'New video uploaded! {latest_video_title}\nWatch it here! @everyone\n{video_url}')
                    print("Notification sent to Discord channel.")
                else:
                    await notification_channel.send(f'New video uploaded! {latest_video_title}\nWatch it here! <@&{notif_role}>\n{video_url}')
                    print("Notification sent to Discord channel.")
            else:
                print(f"ERROR: Channel with ID {dc_id} not found. Please check your .env file.")
    
    except Exception as e:
        print(f"ERROR: An error occurred while checking for new videos: {e}")


# Countdown display loop - shows countdown in terminal
@tasks.loop(seconds=1)  # Update every second
async def countdown_display():
    global next_check_time
    
    if next_check_time is None:
        return
    
    current_time = datetime.datetime.now()
    time_remaining = next_check_time - current_time
    
    if time_remaining.total_seconds() <= 0:
        return
    
    # Calculate total seconds remaining
    total_seconds = int(time_remaining.total_seconds())
    
    # Only show countdown for the last 60 seconds
    if total_seconds <= 60:
        print(f"\rNext YouTube check in: {total_seconds} seconds", end="", flush=True)
    elif total_seconds == 61:
        # Print a newline when countdown ends to separate from next output
        print()  


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
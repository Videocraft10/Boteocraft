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

# Message event
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith('!hello'):
        await message.channel.send(f'Hello {message.author.mention}!')

    # Process commands if any
    await bot.process_commands(message)

bot.run(token, log_handler=handler, log_level=logging.DEBUG)
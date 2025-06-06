import discord
from discord.ext import commands
import os
from utils.permissions import is_manager

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Bot is ready. Logged in as {bot.user}")

# Load Cogs
bot.load_extension("cogs.ign_commands")

bot.run(os.getenv("DISCORD_TOKEN"))

import discord
from discord.ext import commands
import os

# Load the bot token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Enable all intents (requires enabling in Developer Portal)
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Load slash command cogs
    await bot.load_extension("cogs.ign_commands")

    # Sync slash commands with Discord
    await bot.tree.sync()

    print(f"✅ Bot is ready. Logged in as {bot.user}")

# Run the bot
bot.run(TOKEN)

import discord
from discord.ext import commands
import os
import sqlite3

# Load the bot token from the environment
TOKEN = os.getenv("DISCORD_TOKEN")

# Enable all intents (required for role/member operations)
intents = discord.Intents.all()

# Create bot instance with slash command support
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    # ✅ Set up the database and required tables
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            discord_id TEXT PRIMARY KEY,
            ign TEXT,
            union_name TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS union_roles (
            role_name TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS union_leaders (
            role_name TEXT PRIMARY KEY,
            leader_id TEXT
        )
    """)
    conn.commit()
    conn.close()

    # ✅ Load slash command cog
    await bot.load_extension("cogs.commands")
    print("✅ Loaded cogs.commands")

    # ✅ Sync all slash commands globally (no specific guild to avoid 403 error)
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands globally")
    print(f"✅ Bot is ready. Logged in as {bot.user}")


# ✅ Run the bot
bot.run(TOKEN)

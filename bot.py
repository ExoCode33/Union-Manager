import discord
from discord.ext import commands
import os
import sqlite3

# Load your Discord bot token from environment variable
TOKEN = os.getenv("DISCORD_TOKEN")

# Enable all necessary intents
intents = discord.Intents.all()

# Create the bot instance
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    # ✅ Ensure the SQLite database and required tables exist
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

    # ✅ Load all bot command extensions
    await bot.load_extension("cogs.commands")
    print("✅ Loaded cogs.commands")

    # ✅ Sync slash commands globally
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands globally")
    print(f"✅ Bot is ready. Logged in as {bot.user}")


# ✅ Start the bot
bot.run(TOKEN)

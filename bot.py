import discord
from discord.ext import commands
import os
import sqlite3

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # ✅ Ensure database and tables exist with safe column names
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

    # ✅ Load slash command cogs
    await bot.load_extension("cogs.ign_commands")

    # ✅ Sync slash commands with Discord
    await bot.tree.sync()

    print(f"✅ Bot is ready. Logged in as {bot.user}")

# ✅ Start the bot
bot.run(TOKEN)

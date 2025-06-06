import discord
from discord.ext import commands
import os
import sqlite3

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # ✅ Set up SQLite database and tables
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

    # ✅ Load all cog modules
    cog_modules = [
        "cogs.basic_commands",
        "cogs.union_management", 
        "cogs.union_membership",
        "cogs.union_info"
    ]
    
    for module in cog_modules:
        try:
            await bot.load_extension(module)
            print(f"✅ Loaded {module}")
        except Exception as e:
            print(f"❌ Failed to load {module}: {e}")

    # ✅ GLOBAL slash command sync only (no `guild=`!)
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands globally")
    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(TOKEN)

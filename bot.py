import discord
from discord.ext import commands
import os
import sqlite3

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # ✅ Ensure database schema exists
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

    # ✅ Load your merged slash command cog
    await bot.load_extension("cogs.commands")
    print("✅ Loaded cogs.commands")

    # ✅ Force slash command sync to your server only (instant visibility)
    GUILD_ID = 123456789012345678  # 🔁 Replace with your actual Discord server ID
    guild = discord.Object(id=GUILD_ID)
    synced = await bot.tree.sync(guild=guild)

    print(f"✅ Bot is ready. Logged in as {bot.user}")
    print(f"✅ Synced {len(synced)} commands to guild {GUILD_ID}: {[cmd.name for cmd in synced]}")

bot.run(TOKEN)

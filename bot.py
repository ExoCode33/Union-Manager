import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # 🔥 AGGRESSIVE cache clearing - clear commands multiple times
    print("🔄 Clearing command cache...")
    bot.tree.clear_commands(guild=None)
    
    # Also clear for your specific guild if you know the ID
    # Replace YOUR_GUILD_ID with your actual guild ID for instant testing
    # guild = discord.Object(id=YOUR_GUILD_ID)
    # bot.tree.clear_commands(guild=guild)
    
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
    
    # 🔥 Force sync commands (global and guild-specific)
    print("🔄 Syncing commands...")
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands globally")
    
    # For instant testing, also sync to your guild
    # synced_guild = await bot.tree.sync(guild=guild)
    # print(f"✅ Synced {len(synced_guild)} commands to guild")
    
    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(TOKEN)

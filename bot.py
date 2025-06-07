import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    # Clear all commands first to fix caching issues
    bot.tree.clear_commands(guild=None)
    
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
    
    # ✅ Force sync commands globally
    synced = await bot.tree.sync()
    print(f"✅ Synced {len(synced)} commands globally")
    print(f"✅ Bot is ready. Logged in as {bot.user}")

bot.run(TOKEN)

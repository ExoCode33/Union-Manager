import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("🔄 Starting bot initialization...")
    
    # ✅ Load all cog modules FIRST
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
    
    # 🔄 Clear command cache AFTER loading cogs
    print("🔄 Clearing command cache...")
    bot.tree.clear_commands(guild=None)
    
    # 🔄 Sync commands
    print("🔄 Syncing commands...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} commands globally")
        
        # Debug: Show which commands were synced
        if synced:
            command_names = [cmd.name for cmd in synced]
            print(f"📋 Commands synced: {', '.join(command_names)}")
        else:
            print("⚠️ No commands found to sync!")
            
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    print(f"✅ Bot is ready. Logged in as {bot.user}")

# Add this command to manually force sync if needed
@bot.command(name='force_sync')
async def force_sync(ctx):
    """Manual command to force sync slash commands"""
    if not any(role.name.lower() == "admin" for role in ctx.author.roles):
        await ctx.send("❌ Admin only command")
        return
    
    print("🔄 Manual force sync initiated...")
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Force synced {len(synced)} commands")
        print(f"✅ Manual sync completed: {len(synced)} commands")
        if synced:
            command_names = [cmd.name for cmd in synced]
            print(f"📋 Commands: {', '.join(command_names)}")
    except Exception as e:
        await ctx.send(f"❌ Sync failed: {e}")
        print(f"❌ Manual sync failed: {e}")

# Debug command to list loaded commands
@bot.command(name='list_commands')
async def list_commands(ctx):
    """List all loaded slash commands"""
    if not any(role.name.lower() == "admin" for role in ctx.author.roles):
        await ctx.send("❌ Admin only command")
        return
    
    commands = [cmd.name for cmd in bot.tree.get_commands()]
    if commands:
        await ctx.send(f"📋 Loaded commands ({len(commands)}): {', '.join(commands)}")
    else:
        await ctx.send("❌ No commands loaded!")

bot.run(TOKEN)

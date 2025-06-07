import discord
from discord.ext import commands
import os
import traceback

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("🔄 Starting bot initialization...")
    
    # 🔄 Clear command cache FIRST, before loading anything
    print("🔄 Clearing command cache...")
    bot.tree.clear_commands(guild=None)
    
    # ✅ Load all cog modules AFTER clearing cache
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
            
            # Check if commands were added to the tree
            cog = bot.get_cog('BasicCommands')  # This was showing the wrong cog every time
            if module == "cogs.basic_commands":
                cog = bot.get_cog('BasicCommands')
            elif module == "cogs.union_management":
                cog = bot.get_cog('UnionManagement')
            elif module == "cogs.union_membership":
                cog = bot.get_cog('UnionMembership')
            elif module == "cogs.union_info":
                cog = bot.get_cog('UnionInfo')
            
            if cog:
                app_commands = cog.get_app_commands()
                print(f"   📋 Found {len(app_commands)} app commands in {type(cog).__name__}")
                for cmd in app_commands:
                    print(f"      - {cmd.name}: {cmd.description}")
            else:
                print(f"   ⚠️ Could not find cog object for {module}")
                
        except Exception as e:
            print(f"❌ Failed to load {module}: {e}")
            traceback.print_exc()
    
    # Check total commands before sync
    total_commands = len(bot.tree.get_commands())
    print(f"🌳 Total commands in tree ready for sync: {total_commands}")
    
    # List all loaded cogs
    print(f"📁 Loaded cogs: {list(bot.cogs.keys())}")
    
    # 🔄 Sync commands (NO MORE CLEARING!)
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
        traceback.print_exc()
    
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
    
    # Also check cogs
    cog_info = []
    for cog_name, cog in bot.cogs.items():
        cog_commands = [cmd.name for cmd in cog.get_app_commands()]
        cog_info.append(f"{cog_name}: {len(cog_commands)} commands")
    
    if cog_info:
        await ctx.send(f"📁 Cogs: {', '.join(cog_info)}")
    else:
        await ctx.send("❌ No cogs with commands found!")

# Add debug command to manually add cog commands to tree
@bot.command(name='debug_tree')
async def debug_tree(ctx):
    """Debug the command tree"""
    if not any(role.name.lower() == "admin" for role in ctx.author.roles):
        await ctx.send("❌ Admin only command")
        return
    
    print("🔍 Debug: Checking command tree...")
    
    # Check if commands exist in cogs but not in tree
    total_cog_commands = 0
    for cog_name, cog in bot.cogs.items():
        cog_commands = cog.get_app_commands()
        total_cog_commands += len(cog_commands)
        print(f"📁 {cog_name}: {len(cog_commands)} commands")
        for cmd in cog_commands:
            print(f"  - {cmd.name}")
    
    tree_commands = len(bot.tree.get_commands())
    print(f"🌳 Tree has {tree_commands} commands")
    print(f"📊 Total cog commands: {total_cog_commands}")
    
    await ctx.send(f"Debug info printed to console. Tree: {tree_commands}, Cogs: {total_cog_commands}")

# Simple test command that doesn't use database
@bot.tree.command(name="test_bot", description="Test if bot commands work")
async def test_bot(interaction: discord.Interaction):
    await interaction.response.send_message("🎉 Bot is working! Commands can be registered.", ephemeral=True)

bot.run(TOKEN)

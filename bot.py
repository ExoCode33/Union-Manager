import discord
from discord.ext import commands
import os
import traceback
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("🔄 Starting bot initialization...")
    
    # 🔄 Clear command cache FIRST, before loading anything
    print("🔄 Clearing command cache...")
    bot.tree.clear_commands(guild=None)
    
    # Wait a moment for cache to clear
    await asyncio.sleep(1)
    
    # ✅ Load all cog modules AFTER clearing cache
    cog_modules = [
        "cogs.basic_commands",
        "cogs.union_management", 
        "cogs.union_membership",
        "cogs.union_info"
    ]
    
    loaded_cogs = 0
    for module in cog_modules:
        try:
            await bot.load_extension(module)
            print(f"✅ Loaded {module}")
            loaded_cogs += 1
            
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
    
    if total_commands == 0:
        print("❌ WARNING: No commands found in tree! Check cog loading.")
        return
    
    # 🔄 Sync commands with retries
    print("🔄 Syncing commands...")
    max_retries = 3
    for attempt in range(max_retries):
        try:
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} commands globally (attempt {attempt + 1})")
            
            # Debug: Show which commands were synced
            if synced:
                command_names = [cmd.name for cmd in synced]
                print(f"📋 Commands synced: {', '.join(command_names)}")
                
                # Verify specific commands exist
                if 'show_union_leader' in command_names:
                    print("✅ show_union_leader command synced successfully")
                if 'show_union_detail' in command_names:
                    print("✅ show_union_detail command synced successfully")
                    
                break
            else:
                print("⚠️ No commands found to sync!")
                
        except Exception as e:
            print(f"❌ Sync attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying in 2 seconds...")
                await asyncio.sleep(2)
            else:
                print("❌ All sync attempts failed!")
                traceback.print_exc()
    
    print(f"✅ Bot is ready. Logged in as {bot.user}")

# EMERGENCY COMMANDS FOR MANUAL FIXING
@bot.command(name='force_sync')
async def force_sync(ctx):
    """Manual command to force sync slash commands"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ Admin only command")
        return
    
    print("🔄 Manual force sync initiated...")
    await ctx.send("🔄 Starting emergency sync...")
    
    try:
        # Clear and reload cogs
        for cog_name in list(bot.cogs.keys()):
            await bot.unload_extension(f"cogs.{cog_name.lower().replace('commands', 'commands').replace('management', 'management').replace('membership', 'membership').replace('info', 'info')}")
        
        # Clear commands
        bot.tree.clear_commands(guild=None)
        await asyncio.sleep(1)
        
        # Reload cogs
        cog_modules = [
            "cogs.basic_commands",
            "cogs.union_management", 
            "cogs.union_membership",
            "cogs.union_info"
        ]
        
        for module in cog_modules:
            try:
                await bot.load_extension(module)
                print(f"✅ Reloaded {module}")
            except Exception as e:
                print(f"❌ Failed to reload {module}: {e}")
        
        # Sync commands
        synced = await bot.tree.sync()
        await ctx.send(f"✅ **EMERGENCY SYNC COMPLETE**\n📋 Synced {len(synced)} commands\n⏰ Commands will be available in 1-2 minutes")
        
        print(f"✅ Manual sync completed: {len(synced)} commands")
        if synced:
            command_names = [cmd.name for cmd in synced]
            print(f"📋 Commands: {', '.join(command_names)}")
            
    except Exception as e:
        await ctx.send(f"❌ Emergency sync failed: {e}")
        print(f"❌ Manual sync failed: {e}")
        traceback.print_exc()

# Debug command to list loaded commands
@bot.command(name='list_commands')
async def list_commands(ctx):
    """List all loaded slash commands"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ Admin only command")
        return
    
    commands = [cmd.name for cmd in bot.tree.get_commands()]
    if commands:
        await ctx.send(f"📋 **Loaded commands ({len(commands)}):**\n{', '.join(commands)}")
    else:
        await ctx.send("❌ No commands loaded!")
    
    # Also check cogs
    cog_info = []
    for cog_name, cog in bot.cogs.items():
        cog_commands = [cmd.name for cmd in cog.get_app_commands()]
        cog_info.append(f"{cog_name}: {len(cog_commands)} commands")
    
    if cog_info:
        await ctx.send(f"📁 **Cogs:** {', '.join(cog_info)}")
    else:
        await ctx.send("❌ No cogs with commands found!")

# Simple test command that doesn't use database
@bot.tree.command(name="test_bot", description="Test if bot commands work")
async def test_bot(interaction: discord.Interaction):
    await interaction.response.send_message("🎉 Bot is working! Commands can be registered.", ephemeral=True)

# Add error handler for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    print(f"❌ Slash command error: {error}")
    
    if isinstance(error, discord.app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Command not found. Try running `!force_sync` and wait 2 minutes.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ An error occurred: {str(error)}", ephemeral=True)

bot.run(TOKEN)

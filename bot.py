import discord
from discord.ext import commands
import os
import traceback
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")

# Create bot with different client ID approach
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🚀 Bot started: {bot.user} (ID: {bot.user.id})")
    print(f"🎯 In {len(bot.guilds)} guilds")
    
    # NUCLEAR OPTION: Clear everything and start fresh
    print("💥 NUCLEAR SYNC: Clearing ALL commands globally...")
    
    try:
        # Clear all global commands
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        print("✅ Cleared all global commands")
        
        # Wait for Discord to process
        await asyncio.sleep(3)
        
        # Now load cogs one by one with verification
        cog_modules = [
            "cogs.basic_commands",
            "cogs.union_management", 
            "cogs.union_membership", 
            "cogs.union_info"
        ]
        
        for module in cog_modules:
            try:
                print(f"🔄 Loading {module}...")
                await bot.load_extension(module)
                
                # Verify cog loaded
                cog_name_map = {
                    "cogs.basic_commands": "BasicCommands",
                    "cogs.union_management": "UnionManagement",
                    "cogs.union_membership": "UnionMembership", 
                    "cogs.union_info": "UnionInfo"
                }
                
                cog = bot.get_cog(cog_name_map[module])
                if cog:
                    commands = cog.get_app_commands()
                    print(f"   ✅ Loaded {len(commands)} commands from {module}")
                    for cmd in commands:
                        print(f"      - {cmd.name}")
                else:
                    print(f"   ❌ Failed to get cog for {module}")
                    
            except Exception as e:
                print(f"❌ Error loading {module}: {e}")
                traceback.print_exc()
        
        # Check total commands
        total_commands = len(bot.tree.get_commands())
        print(f"\n📊 Total commands ready: {total_commands}")
        
        if total_commands == 0:
            print("💀 CRITICAL: No commands found! Check your cog files.")
            return
        
        # List all commands that will be synced
        print("📋 Commands to sync:")
        for cmd in bot.tree.get_commands():
            print(f"   - {cmd.name}: {cmd.description}")
        
        # NUCLEAR SYNC: Sync commands with aggressive retry
        print("\n💥 NUCLEAR SYNC: Syncing commands...")
        
        for attempt in range(5):  # 5 attempts
            try:
                synced = await bot.tree.sync()
                print(f"✅ SYNC SUCCESS! {len(synced)} commands synced (attempt {attempt + 1})")
                
                if synced:
                    print("🎉 Successfully synced commands:")
                    for cmd in synced:
                        print(f"   ✅ {cmd.name}")
                    
                    # Verify specific problem commands
                    synced_names = [cmd.name for cmd in synced]
                    if 'show_union_leader' in synced_names:
                        print("🎯 show_union_leader is NOW ACTIVE")
                    if 'show_union_detail' in synced_names:
                        print("🎯 show_union_detail is NOW ACTIVE")
                    
                    break
                else:
                    print(f"⚠️ Attempt {attempt + 1}: No commands to sync")
                    
            except discord.HTTPException as e:
                print(f"❌ HTTP Error on attempt {attempt + 1}: {e}")
                if attempt < 4:
                    wait_time = (attempt + 1) * 2
                    print(f"🔄 Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    
            except Exception as e:
                print(f"❌ Sync error on attempt {attempt + 1}: {e}")
                if attempt < 4:
                    await asyncio.sleep(2)
        
        print("\n🚀 Bot ready! Commands should work in 1-2 minutes.")
        
    except Exception as e:
        print(f"💀 NUCLEAR SYNC FAILED: {e}")
        traceback.print_exc()

# EMERGENCY COMMAND - Last resort
@bot.command(name='nuclear_sync')
async def nuclear_sync(ctx):
    """NUCLEAR OPTION: Completely rebuild command tree"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ Admin only")
        return
    
    await ctx.send("💥 **NUCLEAR SYNC INITIATED**\nThis will take 30-60 seconds...")
    
    try:
        # Unload ALL cogs
        cogs_to_unload = list(bot.cogs.keys())
        for cog_name in cogs_to_unload:
            try:
                # Find the module name
                module_map = {
                    "BasicCommands": "cogs.basic_commands",
                    "UnionManagement": "cogs.union_management", 
                    "UnionMembership": "cogs.union_membership",
                    "UnionInfo": "cogs.union_info"
                }
                module = module_map.get(cog_name)
                if module:
                    await bot.unload_extension(module)
                    print(f"🗑️ Unloaded {module}")
            except:
                pass
        
        # Clear everything
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()
        await ctx.send("💥 Cleared all commands...")
        
        await asyncio.sleep(5)  # Wait for Discord
        
        # Reload everything
        cog_modules = [
            "cogs.basic_commands",
            "cogs.union_management", 
            "cogs.union_membership",
            "cogs.union_info"
        ]
        
        loaded = 0
        for module in cog_modules:
            try:
                await bot.load_extension(module)
                loaded += 1
                print(f"♻️ Reloaded {module}")
            except Exception as e:
                print(f"❌ Failed to reload {module}: {e}")
        
        await ctx.send(f"♻️ Reloaded {loaded}/{len(cog_modules)} cogs...")
        
        # Final sync
        synced = await bot.tree.sync()
        await ctx.send(f"🎉 **NUCLEAR SYNC COMPLETE**\n✅ {len(synced)} commands active\n⏰ Wait 2-3 minutes then try your slash commands!")
        
        print(f"💥 Nuclear sync complete: {len(synced)} commands")
        
    except Exception as e:
        await ctx.send(f"💀 Nuclear sync failed: {e}")
        print(f"💀 Nuclear sync error: {e}")

# Super simple test command to verify sync works
@bot.tree.command(name="ping_test", description="Simple ping test")
async def ping_test(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong! Commands are working!", ephemeral=True)

# Manual command list
@bot.command(name='check_commands')
async def check_commands(ctx):
    """Check what commands are loaded"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        return
    
    tree_commands = [cmd.name for cmd in bot.tree.get_commands()]
    cog_commands = {}
    
    for cog_name, cog in bot.cogs.items():
        cog_commands[cog_name] = [cmd.name for cmd in cog.get_app_commands()]
    
    response = f"📊 **Command Status**\n"
    response += f"🌳 **Tree Commands ({len(tree_commands)}):** {', '.join(tree_commands) if tree_commands else 'None'}\n\n"
    
    for cog_name, commands in cog_commands.items():
        response += f"📁 **{cog_name}:** {', '.join(commands) if commands else 'None'}\n"
    
    await ctx.send(response)

bot.run(TOKEN)

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
    print("=" * 60)
    print("🔍 DISCORD BOT DIAGNOSTIC STARTING")
    print("=" * 60)
    
    print(f"🤖 Bot: {bot.user} (ID: {bot.user.id})")
    print(f"📍 Connected to {len(bot.guilds)} guilds:")
    for guild in bot.guilds:
        print(f"   - {guild.name} (ID: {guild.id})")
    
    print("\n" + "=" * 60)
    print("🧪 TEST 1: OAUTH SCOPE CHECK")
    print("=" * 60)
    
    # Test if we can sync at all (this tests OAuth scopes)
    try:
        initial_sync = await bot.tree.sync()
        print(f"✅ Basic sync WORKS: {len(initial_sync)} commands synced")
        print("✅ OAuth scopes are correct (bot has 'applications.commands')")
    except discord.Forbidden as e:
        print(f"❌ SYNC FORBIDDEN: {e}")
        print("❌ PROBLEM: Bot missing 'applications.commands' OAuth scope")
        print("🔧 SOLUTION: Re-invite bot with correct OAuth URL")
        print("=" * 60)
        return
    except Exception as e:
        print(f"❌ SYNC ERROR: {e}")
        print("❌ Unknown sync issue")
        return
    
    print("\n" + "=" * 60)
    print("🧪 TEST 2: SIMPLE COMMAND CREATION")
    print("=" * 60)
    
    # Create a simple test command
    @bot.tree.command(name="diagnostic_test", description="Diagnostic test command")
    async def diagnostic_test(interaction: discord.Interaction):
        await interaction.response.send_message("🎉 Diagnostic test successful!", ephemeral=True)
    
    print("✅ Created diagnostic_test command")
    
    # Sync the simple command
    try:
        simple_sync = await bot.tree.sync()
        print(f"✅ Simple command sync: {len(simple_sync)} commands")
        if "diagnostic_test" in [cmd.name for cmd in simple_sync]:
            print("✅ diagnostic_test command is active in Discord")
        else:
            print("❌ diagnostic_test command not found in sync result")
    except Exception as e:
        print(f"❌ Simple command sync failed: {e}")
    
    print("\n" + "=" * 60)
    print("🧪 TEST 3: FILE STRUCTURE CHECK")
    print("=" * 60)
    
    # Check if cog files exist
    required_files = [
        "cogs/basic_commands.py",
        "cogs/union_management.py", 
        "cogs/union_membership.py",
        "cogs/union_info.py",
        "utils/__init__.py",
        "utils/db.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n❌ PROBLEM: {len(missing_files)} required files missing")
        print("🔧 SOLUTION: Create missing files")
        return
    
    print("\n" + "=" * 60)
    print("🧪 TEST 4: DATABASE CONNECTION")
    print("=" * 60)
    
    # Test database connection
    try:
        from utils.db import get_connection
        conn = await get_connection()
        await conn.close()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("❌ PROBLEM: Database connection issue")
        print("🔧 SOLUTION: Check DATABASE_URL environment variable")
        # Continue anyway, might be cog loading issue
    
    print("\n" + "=" * 60)
    print("🧪 TEST 5: COG LOADING TEST")
    print("=" * 60)
    
    # Test loading each cog individually
    cog_modules = [
        ("cogs.basic_commands", "BasicCommands"),
        ("cogs.union_management", "UnionManagement"),
        ("cogs.union_membership", "UnionMembership"), 
        ("cogs.union_info", "UnionInfo")
    ]
    
    loaded_cogs = []
    failed_cogs = []
    total_commands = 0
    
    for module_name, cog_class_name in cog_modules:
        try:
            print(f"\n🔄 Loading {module_name}...")
            await bot.load_extension(module_name)
            
            # Verify cog loaded
            cog = bot.get_cog(cog_class_name)
            if cog:
                commands = cog.get_app_commands()
                command_count = len(commands)
                total_commands += command_count
                
                print(f"✅ {module_name} loaded successfully")
                print(f"   📋 Found {command_count} commands:")
                for cmd in commands:
                    print(f"      - {cmd.name}: {cmd.description}")
                
                loaded_cogs.append(module_name)
            else:
                print(f"❌ {module_name} loaded but cog class '{cog_class_name}' not found")
                failed_cogs.append(module_name)
                
        except Exception as e:
            print(f"❌ {module_name} failed to load: {e}")
            print("   Error details:")
            traceback.print_exc()
            failed_cogs.append(module_name)
    
    print(f"\n📊 COG LOADING SUMMARY:")
    print(f"   ✅ Loaded: {len(loaded_cogs)}/{len(cog_modules)}")
    print(f"   ❌ Failed: {len(failed_cogs)}")
    print(f"   📋 Total commands: {total_commands}")
    
    if failed_cogs:
        print(f"\n❌ FAILED COGS: {', '.join(failed_cogs)}")
        print("🔧 SOLUTION: Fix the errors shown above")
    
    print("\n" + "=" * 60)
    print("🧪 TEST 6: FINAL COMMAND SYNC")
    print("=" * 60)
    
    # Check commands in tree before sync
    tree_commands = bot.tree.get_commands()
    print(f"📋 Commands in tree before sync: {len(tree_commands)}")
    for cmd in tree_commands:
        print(f"   - {cmd.name}")
    
    if len(tree_commands) == 0:
        print("❌ PROBLEM: No commands in tree!")
        print("❌ This means cogs loaded but commands weren't added")
        print("🔧 SOLUTION: Check cog setup() functions")
    
    # Final sync attempt
    try:
        final_sync = await bot.tree.sync()
        print(f"\n✅ FINAL SYNC: {len(final_sync)} commands synced to Discord")
        
        synced_names = [cmd.name for cmd in final_sync]
        target_commands = ["show_union_leader", "show_union_detail"]
        
        print("\n🎯 TARGET COMMAND CHECK:")
        for target in target_commands:
            if target in synced_names:
                print(f"   ✅ {target} is ACTIVE in Discord")
            else:
                print(f"   ❌ {target} NOT FOUND in Discord")
        
        if len(final_sync) > 0:
            print(f"\n📋 ALL SYNCED COMMANDS:")
            for cmd in final_sync:
                print(f"   - {cmd.name}")
        
    except Exception as e:
        print(f"❌ Final sync failed: {e}")
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎯 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    if len(failed_cogs) == 0 and total_commands > 0:
        print("✅ ALL TESTS PASSED!")
        print("✅ Bot should be working correctly")
        print("⏰ Wait 2-3 minutes for Discord to update slash commands")
    elif len(failed_cogs) > 0:
        print("❌ SOME COGS FAILED TO LOAD")
        print("🔧 Fix the cog loading errors above")
    elif total_commands == 0:
        print("❌ NO COMMANDS FOUND")
        print("🔧 Check that cogs are creating commands properly")
    else:
        print("⚠️ MIXED RESULTS - Check individual test results above")
    
    print("\n💡 NEXT STEPS:")
    print("1. If OAuth scope error: Re-invite bot with 'applications.commands'")
    print("2. If cog errors: Fix the Python errors shown")
    print("3. If all tests pass: Wait 2-3 minutes then try /diagnostic_test")
    print("4. After waiting, try your /show_union_leader command")
    
    print("\n" + "=" * 60)
    print("🔍 DIAGNOSTIC COMPLETE")
    print("=" * 60)

# Test prefix command
@bot.command(name='diag_prefix')
async def diag_prefix(ctx):
    """Test if prefix commands work"""
    await ctx.send("✅ Prefix commands are working! This means the bot is connected properly.")

# Emergency commands
@bot.command(name='diag_sync')
async def diag_sync(ctx):
    """Emergency sync command"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ Admin only")
        return
    
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"🔧 Emergency sync: {len(synced)} commands")
    except Exception as e:
        await ctx.send(f"❌ Emergency sync failed: {e}")

if __name__ == "__main__":
    print("🔍 Starting Discord Bot Diagnostic...")
    print("This will test all aspects of your bot setup.")
    print("Press Ctrl+C to cancel, or wait 3 seconds to continue...")
    
    try:
        import time
        time.sleep(3)
        print("\n🚀 Starting diagnostic bot...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n❌ Diagnostic cancelled by user")
    except Exception as e:
        print(f"\n❌ Diagnostic failed to start: {e}")
        print("\n🔧 Common issues:")
        print("1. DISCORD_TOKEN not set in environment")
        print("2. Invalid bot token") 
        print("3. Bot not invited to any servers")
        print("4. Missing required Python packages (discord.py, asyncpg)")

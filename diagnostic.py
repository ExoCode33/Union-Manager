import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging

# Setup logging for diagnostic
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

class DiagnosticReport:
    """Class to track diagnostic results"""
    def __init__(self):
        self.oauth_status = False
        self.file_structure_status = True
        self.database_status = False
        self.cog_loading_results = {}
        self.total_commands = 0
        self.sync_status = False
        self.missing_files = []
        self.failed_cogs = []

@bot.event
async def on_ready():
    report = DiagnosticReport()
    
    print("=" * 60)
    print("🔍 DISCORD BOT DIAGNOSTIC TOOL")
    print("=" * 60)
    
    logger.info(f"Bot: {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} (ID: {guild.id})")
    
    # Test 1: OAuth Scope Verification
    print("\n" + "=" * 60)
    print("TEST 1: OAUTH SCOPE VERIFICATION")
    print("=" * 60)
    
    try:
        initial_sync = await bot.tree.sync()
        logger.info(f"OAuth scope test passed: {len(initial_sync)} commands synced")
        report.oauth_status = True
        print("✅ OAuth scopes are correctly configured")
        print("✅ Bot has 'applications.commands' permission")
    except discord.Forbidden as e:
        logger.error(f"OAuth scope test failed: {e}")
        report.oauth_status = False
        print("❌ CRITICAL: Bot missing 'applications.commands' OAuth scope")
        print("🔧 SOLUTION: Re-invite bot with correct OAuth permissions")
        print("=" * 60)
        return report
    except Exception as e:
        logger.error(f"Unexpected sync error: {e}")
        print(f"❌ Unexpected synchronization error: {e}")
        return report
    
    # Test 2: Simple Command Creation
    print("\n" + "=" * 60)
    print("TEST 2: COMMAND CREATION VERIFICATION")
    print("=" * 60)
    
    @bot.tree.command(name="diagnostic_check", description="Diagnostic verification command")
    async def diagnostic_check(interaction: discord.Interaction):
        await interaction.response.send_message("🎯 Diagnostic test successful!", ephemeral=True)
    
    try:
        test_sync = await bot.tree.sync()
        if "diagnostic_check" in [cmd.name for cmd in test_sync]:
            print("✅ Command creation and synchronization working correctly")
        else:
            print("⚠️ Command created but not found in synchronization result")
    except Exception as e:
        logger.error(f"Command creation test failed: {e}")
        print(f"❌ Command creation test failed: {e}")
    
    # Test 3: File Structure Verification
    print("\n" + "=" * 60)
    print("TEST 3: FILE STRUCTURE VERIFICATION")
    print("=" * 60)
    
    required_files = [
        "cogs/basic_commands.py",
        "cogs/union_management.py", 
        "cogs/union_membership.py",
        "cogs/union_info.py",
        "utils/__init__.py",
        "utils/db.py"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"Found: {file_path}")
            print(f"✅ {file_path}")
        else:
            logger.warning(f"Missing: {file_path}")
            print(f"❌ MISSING: {file_path}")
            report.missing_files.append(file_path)
            report.file_structure_status = False
    
    if report.missing_files:
        print(f"\n❌ ISSUE: {len(report.missing_files)} required files missing")
        print("🔧 SOLUTION: Ensure all required files are present")
        return report
    
    print("✅ All required files present")
    
    # Test 4: Database Connection Test
    print("\n" + "=" * 60)
    print("TEST 4: DATABASE CONNECTION TEST")
    print("=" * 60)
    
    try:
        from utils.db import get_connection
        conn = await get_connection()
        await conn.close()
        logger.info("Database connection successful")
        print("✅ Database connection established successfully")
        report.database_status = True
    except ImportError as e:
        logger.error(f"Database module import failed: {e}")
        print(f"❌ Cannot import database module: {e}")
        print("🔧 Check utils/db.py file structure")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        print(f"❌ Database connection failed: {e}")
        print("🔧 Verify DATABASE_URL environment variable")
        print("⚠️ Continuing diagnostic (some features may not work)")
    
    # Test 5: Module Loading Test
    print("\n" + "=" * 60)
    print("TEST 5: MODULE LOADING VERIFICATION")
    print("=" * 60)
    
    cog_modules = [
        ("cogs.basic_commands", "BasicCommands"),
        ("cogs.union_management", "UnionManagement"),
        ("cogs.union_membership", "UnionMembership"), 
        ("cogs.union_info", "UnionInfo")
    ]
    
    for module_name, cog_class_name in cog_modules:
        try:
            logger.info(f"Loading {module_name}...")
            print(f"\n🔄 Testing {module_name}...")
            
            await bot.load_extension(module_name)
            
            # Verify cog loaded correctly
            cog = bot.get_cog(cog_class_name)
            if cog:
                commands = cog.get_app_commands()
                command_count = len(commands)
                report.total_commands += command_count
                
                logger.info(f"{module_name} loaded: {command_count} commands")
                print(f"✅ {module_name}: {command_count} commands loaded")
                
                # List commands for verification
                for cmd in commands:
                    print(f"   - {cmd.name}: {cmd.description}")
                
                report.cog_loading_results[module_name] = {
                    'status': 'success',
                    'commands': command_count,
                    'command_names': [cmd.name for cmd in commands]
                }
            else:
                logger.error(f"{module_name} loaded but cog class not found")
                print(f"❌ {module_name}: Module loaded but cog class '{cog_class_name}' not accessible")
                report.failed_cogs.append(module_name)
                report.cog_loading_results[module_name] = {
                    'status': 'failed',
                    'error': 'Cog class not found'
                }
                
        except Exception as e:
            logger.error(f"{module_name} loading failed: {str(e)}")
            print(f"❌ {module_name}: Loading failed")
            print(f"   Error: {str(e)}")
            
            # Show detailed error for debugging
            error_details = traceback.format_exc()
            print(f"   Details: {error_details.splitlines()[-2] if error_details.splitlines() else 'Unknown error'}")
            
            report.failed_cogs.append(module_name)
            report.cog_loading_results[module_name] = {
                'status': 'failed',
                'error': str(e)
            }
    
    # Test 6: Final Synchronization Test
    print("\n" + "=" * 60)
    print("TEST 6: FINAL SYNCHRONIZATION VERIFICATION")
    print("=" * 60)
    
    tree_commands = bot.tree.get_commands()
    logger.info(f"Commands in tree: {len(tree_commands)}")
    print(f"📋 Commands ready for synchronization: {len(tree_commands)}")
    
    if len(tree_commands) == 0:
        print("❌ CRITICAL: No commands found in command tree")
        print("🔧 Review module loading errors above")
    else:
        print("✅ Commands successfully registered in tree")
        
        # List all commands
        for cmd in tree_commands:
            print(f"   - {cmd.name}")
    
    # Perform final synchronization
    try:
        final_sync = await bot.tree.sync()
        synced_count = len(final_sync)
        logger.info(f"Final sync completed: {synced_count} commands")
        print(f"\n✅ Synchronization successful: {synced_count} commands")
        
        # Verify critical commands
        synced_names = [cmd.name for cmd in final_sync]
        critical_commands = ["show_union_leader", "show_union_detail"]
        
        print("\n🎯 Critical Command Verification:")
        for critical_cmd in critical_commands:
            if critical_cmd in synced_names:
                print(f"   ✅ {critical_cmd}: Available in Discord")
            else:
                print(f"   ❌ {critical_cmd}: Not found in synchronization")
        
        if synced_count > 0:
            report.sync_status = True
            print(f"\n📋 All synchronized commands:")
            for cmd in final_sync:
                print(f"   - {cmd.name}")
        
    except Exception as e:
        logger.error(f"Final synchronization failed: {e}")
        print(f"❌ Final synchronization failed: {e}")
    
    # Generate Final Report
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    print(f"OAuth Status: {'✅ PASS' if report.oauth_status else '❌ FAIL'}")
    print(f"File Structure: {'✅ PASS' if report.file_structure_status else '❌ FAIL'}")
    print(f"Database Connection: {'✅ PASS' if report.database_status else '⚠️ WARN'}")
    print(f"Module Loading: {'✅ PASS' if len(report.failed_cogs) == 0 else '❌ FAIL'}")
    print(f"Command Sync: {'✅ PASS' if report.sync_status else '❌ FAIL'}")
    print(f"Total Commands: {report.total_commands}")
    
    if report.failed_cogs:
        print(f"\n❌ Failed Modules: {', '.join(report.failed_cogs)}")
    
    # Overall status
    all_critical_passed = (report.oauth_status and 
                          report.file_structure_status and 
                          len(report.failed_cogs) == 0 and 
                          report.sync_status)
    
    if all_critical_passed:
        print("\n🎉 DIAGNOSTIC RESULT: ALL SYSTEMS OPERATIONAL")
        print("✅ Bot should function correctly")
        print("⏰ Commands will be available in Discord within 1-2 minutes")
    else:
        print("\n⚠️ DIAGNOSTIC RESULT: ISSUES DETECTED")
        print("🔧 Review failed tests above and address issues")
        
        # Specific recommendations
        if not report.oauth_status:
            print("🔧 Priority 1: Fix OAuth scope issues")
        if not report.file_structure_status:
            print("🔧 Priority 2: Add missing files")
        if report.failed_cogs:
            print("🔧 Priority 3: Fix module loading errors")
    
    print("\n💡 Next Steps:")
    if all_critical_passed:
        print("1. Wait 2-3 minutes for Discord to update")
        print("2. Test /diagnostic_check command in Discord")
        print("3. Try your main bot commands")
    else:
        print("1. Address the failed tests shown above")
        print("2. Re-run diagnostic after fixes")
        print("3. Contact support if issues persist")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)

# Test prefix command
@bot.command(name='test')
async def test_prefix(ctx):
    """Test prefix command functionality"""
    await ctx.send("✅ Prefix commands working correctly")

def main():
    """Main diagnostic function"""
    if not TOKEN:
        print("❌ DISCORD_TOKEN environment variable not set")
        return
    
    print("🔍 Starting comprehensive bot diagnostic...")
    print("This will test all critical bot systems and components.")
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n❌ Diagnostic cancelled by user")
    except discord.LoginFailure:
        print("\n❌ Invalid bot token - check DISCORD_TOKEN")
    except Exception as e:
        print(f"\n❌ Diagnostic failed to start: {e}")
        print("\n🔧 Common issues:")
        print("1. Invalid or missing DISCORD_TOKEN")
        print("2. Network connectivity problems")
        print("3. Missing required dependencies")

if __name__ == "__main__":
    main()

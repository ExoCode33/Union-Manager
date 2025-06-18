import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging
import datetime

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Bot status tracking
class BotStatus:
    def __init__(self):
        self.startup_time = None
        self.commands_synced = 0
        self.last_sync_time = None
        self.modules_loaded = 0
        self.sync_errors = 0

bot_status = BotStatus()

async def debug_commands():
    """Debug function to check if commands are properly registered"""
    try:
        print("\n" + "="*60)
        print("🔍 COMMAND REGISTRATION DEBUG")
        print("="*60)
        
        # Check commands in tree
        tree_commands = bot.tree.get_commands()
        print(f"📊 Commands in bot.tree: {len(tree_commands)}")
        
        if tree_commands:
            print("\n🌳 Commands in tree:")
            for i, cmd in enumerate(tree_commands, 1):
                print(f"  {i:2d}. {cmd.name}")
                print(f"      Description: {cmd.description}")
                print(f"      Parameters: {[param.name for param in cmd.parameters]}")
                print()
        else:
            print("❌ NO COMMANDS FOUND IN TREE!")
        
        # Check cogs and their commands
        print(f"\n🧩 Loaded cogs: {len(bot.cogs)}")
        total_cog_commands = 0
        
        for cog_name, cog in bot.cogs.items():
            app_commands = cog.get_app_commands()
            total_cog_commands += len(app_commands)
            print(f"\n📦 {cog_name}: {len(app_commands)} commands")
            
            if app_commands:
                for j, cmd in enumerate(app_commands, 1):
                    print(f"    {j}. {cmd.name} - {cmd.description}")
            else:
                print("    ❌ No app commands found in this cog")
        
        print(f"\n📈 SUMMARY:")
        print(f"  Total cogs: {len(bot.cogs)}")
        print(f"  Commands from cogs: {total_cog_commands}")
        print(f"  Commands in tree: {len(tree_commands)}")
        print(f"  Discrepancy: {total_cog_commands - len(tree_commands)}")
        
        if total_cog_commands != len(tree_commands):
            print("⚠️ MISMATCH DETECTED: Commands in cogs don't match commands in tree!")
        else:
            print("✅ Command counts match between cogs and tree")
        
        print("="*60)
        print()
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
        print(traceback.format_exc())

@bot.event
async def on_ready():
    """Clean bot initialization - Guild-specific commands only (no duplicates)"""
    try:
        # Set startup time
        bot_status.startup_time = datetime.datetime.now(datetime.timezone.utc)
        
        logger.info("============================================================")
        logger.info("DISCORD UNION BOT INITIALIZATION")
        logger.info("============================================================")
        logger.info(f"Bot: {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guilds")
        
        # Log guild information and permissions
        for guild in bot.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
            
            # Check bot permissions in each guild
            bot_member = guild.get_member(bot.user.id)
            if bot_member:
                perms = bot_member.guild_permissions
                logger.info(f"    Permissions: Admin={perms.administrator}, SendMessages={perms.send_messages}")
        
        # Clear ALL existing commands (global and guild-specific)
        logger.info("Clearing all existing commands...")
        bot.tree.clear_commands(guild=None)  # Clear global
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)  # Clear guild-specific
        await asyncio.sleep(1)
        
        # Load all command modules
        logger.info("Loading command modules...")
        modules = [
            "cogs.basic_commands",
            "cogs.union_management", 
            "cogs.union_membership",
            "cogs.union_info"
        ]
        
        loaded_modules = 0
        total_commands = 0
        
        for module in modules:
            try:
                logger.info(f"Loading {module}...")
                await bot.load_extension(module)
                loaded_modules += 1
                
            except Exception as e:
                logger.error(f"  ❌ Failed to load {module}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Update status
        bot_status.modules_loaded = loaded_modules
        total_commands = len(bot.tree.get_commands())
        
        logger.info("========================================")
        logger.info("Module Loading Summary:")
        logger.info(f"  Successful: {loaded_modules}/{len(modules)}")
        logger.info(f"  Failed: {len(modules) - loaded_modules}")
        logger.info(f"  Total Commands: {total_commands}")
        
        # DEBUG: Check command registration
        await debug_commands()
        
        # Verify command tree
        commands_in_tree = len(bot.tree.get_commands())
        logger.info(f"Commands ready: {commands_in_tree}")
        
        if commands_in_tree > 0:
            logger.info("Commands to sync:")
            for cmd in bot.tree.get_commands():
                logger.info(f"  - {cmd.name}: {cmd.description}")
        else:
            logger.error("❌ NO COMMANDS IN TREE - SYNC WILL FAIL")
        
        logger.info("========================================")
        logger.info("Starting GUILD-ONLY synchronization (no duplicates)...")
        
        # GUILD-ONLY sync - no global commands
        sync_success = False
        
        for guild in bot.guilds:
            try:
                logger.info(f"Syncing commands to guild: {guild.name}")
                
                # DEBUG: Check what we're about to sync
                pre_sync_commands = bot.tree.get_commands(guild=guild)
                logger.info(f"Pre-sync: {len(pre_sync_commands)} commands for {guild.name}")
                
                # Sync only to this specific guild (not globally)
                synced = await bot.tree.sync(guild=guild)
                
                logger.info(f"✅ Guild sync successful: {len(synced)} commands to {guild.name}")
                
                if synced:
                    logger.info(f"Synced commands: {', '.join([cmd.name for cmd in synced])}")
                    
                    # Verify critical commands
                    critical_commands = ["show_union_leader", "show_union_detail"]
                    for cmd_name in critical_commands:
                        if any(cmd.name == cmd_name for cmd in synced):
                            logger.info(f"  ✅ Critical command '{cmd_name}' available in {guild.name}")
                        else:
                            logger.warning(f"  ⚠️ Critical command '{cmd_name}' missing in {guild.name}")
                else:
                    logger.error(f"❌ No commands were synced to {guild.name}")
                    logger.error("This usually means:")
                    logger.error("  1. Commands are not properly registered in the tree")
                    logger.error("  2. Bot lacks necessary permissions")
                    logger.error("  3. Discord API rate limiting")
                
                # Update status
                bot_status.commands_synced = len(synced)
                bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
                sync_success = True
                
            except Exception as e:
                logger.error(f"❌ Guild sync failed for {guild.name}: {str(e)}")
                logger.error(traceback.format_exc())
                bot_status.sync_errors += 1
        
        # Final status report
        logger.info("========================================")
        if sync_success:
            logger.info("🎉 BOT INITIALIZATION COMPLETE")
            logger.info(f"✅ {loaded_modules} modules loaded")
            logger.info(f"✅ {bot_status.commands_synced} commands synchronized per guild")
            logger.info(f"✅ Connected to {len(bot.guilds)} guilds")
            logger.info("✅ NO DUPLICATE COMMANDS - Guild-specific only")
            
            if bot_status.commands_synced > 0:
                logger.info("Commands will be available in Discord within 1-2 minutes")
            else:
                logger.warning("⚠️ NO COMMANDS SYNCED - Check debug output above")
        else:
            logger.warning("⚠️ BOT STARTED WITH SYNC ISSUES")
            logger.warning("Use !clean_sync to manually sync")
        
        logger.info("============================================================")
        
    except Exception as e:
        logger.error(f"Critical error during bot initialization: {str(e)}")
        logger.error(traceback.format_exc())

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling with detailed logging"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    
    else:
        # Log unexpected errors
        logger.error(f"Command error in {ctx.command}: {str(error)}")
        logger.error(traceback.format_exc())
        await ctx.send(f"❌ An unexpected error occurred: {str(error)}")

# ============================================================
# CLEAN SYNC COMMANDS (NO DUPLICATES)
# ============================================================

@bot.command(name='debug_sync')
async def debug_sync(ctx):
    """Debug sync command to check what's happening"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🔍 **STARTING DEBUG SYNC...**")
        
        # Run debug function
        await debug_commands()
        
        guild = ctx.guild
        
        # Check current state
        tree_commands = len(bot.tree.get_commands())
        guild_commands = len(bot.tree.get_commands(guild=guild))
        
        debug_msg = f"""📊 **DEBUG INFORMATION:**

**Tree Commands:** {tree_commands}
**Guild Commands:** {guild_commands}
**Loaded Cogs:** {len(bot.cogs)}

**Cogs:** {', '.join(bot.cogs.keys())}

**Tree Commands List:**
{chr(10).join([f'• {cmd.name}' for cmd in bot.tree.get_commands()]) if bot.tree.get_commands() else 'None'}"""

        await ctx.send(debug_msg)
        
        # Try to sync
        await ctx.send("🔄 Attempting sync...")
        synced = await bot.tree.sync(guild=guild)
        
        await ctx.send(f"✅ **Sync result:** {len(synced)} commands synced")
        
        if synced:
            sync_list = '\n'.join([f'• {cmd.name}' for cmd in synced])
            await ctx.send(f"**Synced commands:**\n{sync_list}")
        
    except Exception as e:
        await ctx.send(f"❌ Debug sync failed: {str(e)}")
        logger.error(f"Debug sync error: {str(e)}")
        logger.error(traceback.format_exc())

@bot.command(name='clean_sync')
async def clean_sync(ctx):
    """Clean sync - Guild-specific commands only, no duplicates (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🧹 **CLEAN SYNC STARTING...**\n*Removing duplicates and syncing guild-specific only*")
        
        guild = ctx.guild
        
        # Step 1: Clear global commands completely
        logger.info("Clearing global commands...")
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()  # Empty global sync
        
        # Step 2: Clear guild commands
        logger.info(f"Clearing guild commands for {guild.name}...")
        bot.tree.clear_commands(guild=guild)
        
        # Step 3: Sync only to this guild
        logger.info(f"Syncing to guild only: {guild.name}")
        synced = await bot.tree.sync(guild=guild)
        
        success_msg = f"""✅ **CLEAN SYNC COMPLETE!**

🧹 **No Duplicates:** Guild-specific commands only
✅ **Guild:** {guild.name}
✅ **Commands Available:** {len(synced)}

**Commands synced:**
{', '.join([f'`/{cmd.name}`' for cmd in synced[:10]])}
{'...' if len(synced) > 10 else ''}

⏰ **Commands will appear in 1-2 minutes**
🎯 **No duplicate commands!**"""
        
        await ctx.send(success_msg)
        
        logger.info(f"✅ Clean sync successful: {len(synced)} commands to {guild.name}")
        logger.info(f"Synced commands: {[cmd.name for cmd in synced]}")
        
        # Update status
        bot_status.commands_synced = len(synced)
        bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
        
    except Exception as e:
        error_msg = f"❌ **Clean sync failed:** {str(e)}"
        await ctx.send(error_msg)
        logger.error(f"Clean sync error: {str(e)}")
        logger.error(traceback.format_exc())

@bot.command(name='remove_duplicates')
async def remove_duplicates(ctx):
    """Remove duplicate commands by clearing global and keeping guild-specific (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🧹 **REMOVING DUPLICATES...**")
        
        # Clear global commands only (keep guild commands)
        bot.tree.clear_commands(guild=None)
        global_cleared = await bot.tree.sync()  # Empty global sync
        
        await ctx.send(f"✅ **Duplicates removed!** Global commands cleared.\n🎯 Only guild-specific commands remain (no duplicates)")
        
        logger.info("Duplicate removal: Global commands cleared, guild commands retained")
        
    except Exception as e:
        await ctx.send(f"❌ **Duplicate removal failed:** {str(e)}")
        logger.error(f"Duplicate removal error: {str(e)}")

@bot.command(name='check_duplicates')
async def check_duplicates(ctx):
    """Check for duplicate commands (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        guild = ctx.guild
        
        # Get global and guild commands
        global_commands = bot.tree.get_commands()
        guild_commands = bot.tree.get_commands(guild=guild)
        
        # Find duplicates
        global_names = {cmd.name for cmd in global_commands}
        guild_names = {cmd.name for cmd in guild_commands}
        duplicates = global_names.intersection(guild_names)
        
        if duplicates:
            duplicate_list = ', '.join([f'`{name}`' for name in duplicates])
            duplicate_msg = f"""⚠️ **DUPLICATES FOUND:**

**Global Commands:** {len(global_commands)}
**Guild Commands:** {len(guild_commands)}
**Duplicated:** {len(duplicates)}

**Duplicate commands:**
{duplicate_list}

**Fix:** Run `!remove_duplicates` or `!clean_sync`"""
        else:
            duplicate_msg = f"""✅ **NO DUPLICATES FOUND:**

**Global Commands:** {len(global_commands)}
**Guild Commands:** {len(guild_commands)}
**Status:** Clean - no duplicate commands"""
        
        await ctx.send(duplicate_msg)
        
    except Exception as e:
        await ctx.send(f"❌ Duplicate check failed: {str(e)}")

@bot.command(name='bot_status')
async def bot_status_command(ctx):
    """Display comprehensive bot status (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        # Calculate uptime
        uptime = "Unknown"
        if bot_status.startup_time:
            uptime_delta = datetime.datetime.now(datetime.timezone.utc) - bot_status.startup_time
            hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime = f"{hours}h {minutes}m {seconds}s"
        
        # Get command counts
        guild = ctx.guild
        global_commands = len(bot.tree.get_commands())
        guild_commands = len(bot.tree.get_commands(guild=guild))
        
        # Format last sync time
        last_sync = "Never"
        if bot_status.last_sync_time:
            last_sync = bot_status.last_sync_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        status_embed = discord.Embed(
            title="🤖 Bot Status Dashboard",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        
        status_embed.add_field(
            name="⏱️ System Status",
            value=f"""**Uptime:** {uptime}
**Guilds:** {len(bot.guilds)}
**Modules Loaded:** {bot_status.modules_loaded}""",
            inline=True
        )
        
        status_embed.add_field(
            name="⚙️ Commands",
            value=f"""**Global Commands:** {global_commands}
**Guild Commands:** {guild_commands}
**Sync Errors:** {bot_status.sync_errors}""",
            inline=True
        )
        
        status_embed.add_field(
            name="🧹 Duplicate Status",
            value="✅ Clean" if global_commands == 0 else "⚠️ May have duplicates",
            inline=True
        )
        
        status_embed.add_field(
            name="🕐 Last Sync",
            value=last_sync,
            inline=False
        )
        
        await ctx.send(embed=status_embed)
        
    except Exception as e:
        await ctx.send(f"❌ Status display failed: {str(e)}")

# ============================================================
# BASIC SLASH COMMANDS
# ============================================================

@bot.tree.command(name="ping", description="Test bot responsiveness")
async def ping(interaction: discord.Interaction):
    """Basic ping command for testing"""
    try:
        latency = round(bot.latency * 1000)
        await interaction.response.send_message(f"🏓 **Pong!** Latency: {latency}ms")
    except Exception as e:
        await interaction.response.send_message(f"❌ Ping failed: {str(e)}", ephemeral=True)

@bot.tree.command(name="bot_info", description="Display bot information")
async def bot_info(interaction: discord.Interaction):
    """Display bot information"""
    try:
        guild = interaction.guild
        global_commands = len(bot.tree.get_commands())
        guild_commands = len(bot.tree.get_commands(guild=guild))
        
        embed = discord.Embed(
            title="🤖 Union Bot Information",
            description="Discord Union Management Bot - Clean Version",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👤 Bot", value=f"{bot.user.name}#{bot.user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=str(bot.user.id), inline=True)
        embed.add_field(name="🏠 Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="⚙️ Global Commands", value=str(global_commands), inline=True)
        embed.add_field(name="🎯 Guild Commands", value=str(guild_commands), inline=True)
        embed.add_field(name="🧹 Status", value="✅ No Duplicates" if global_commands == 0 else "⚠️ Check duplicates", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Info display failed: {str(e)}", ephemeral=True)

# ============================================================
# PREFIX COMMANDS FOR TESTING
# ============================================================

@bot.command(name='ping')
async def ping_prefix(ctx):
    """Prefix version of ping for testing"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 **Pong!** Latency: {latency}ms")

@bot.command(name='help_clean')
async def help_clean(ctx):
    """Show clean sync commands"""
    help_msg = """🧹 **CLEAN SYNC COMMANDS:**

**!debug_sync** - Debug command registration and sync issues
**!clean_sync** - Remove duplicates and sync guild-specific only
**!remove_duplicates** - Remove global commands (keep guild commands)
**!check_duplicates** - Check for duplicate commands
**!bot_status** - View bot status and duplicate status

🎯 **Goal:** One copy of each command per guild (no duplicates)"""
    
    await ctx.send(help_msg)

# ============================================================
# BOT STARTUP
# ============================================================

async def main():
    """Main bot startup function with enhanced error handling"""
    try:
        if not TOKEN:
            logger.error("❌ DISCORD_TOKEN environment variable not found!")
            logger.error("Please set your bot token in the .env file")
            return
        
        logger.info("Starting Discord Union Bot (Clean Version - No Duplicates)...")
        await bot.start(TOKEN)
        
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token!")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {str(e)}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical startup error: {str(e)}")
        logger.error(traceback.format_exc())

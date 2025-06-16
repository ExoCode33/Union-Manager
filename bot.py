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

@bot.event
async def on_ready():
    """Enhanced bot initialization with comprehensive logging and multi-stage sync"""
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
        
        # Clear existing command state for fresh start
        logger.info("Clearing existing command state...")
        bot.tree.clear_commands(guild=None)
        await asyncio.sleep(1)  # Brief pause
        
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
                
                # Count commands from this module
                module_commands = len([cmd for cmd in bot.tree.get_commands() if getattr(cmd, 'module', '').startswith(module.split('.')[-1])])
                logger.info(f"  ✅ {module}: {module_commands} commands loaded")
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
        
        # Verify command tree
        commands_in_tree = len(bot.tree.get_commands())
        logger.info(f"Commands in tree: {commands_in_tree}")
        
        if commands_in_tree > 0:
            logger.info("Commands ready for synchronization:")
            for cmd in bot.tree.get_commands():
                logger.info(f"  - {cmd.name}: {cmd.description}")
        
        logger.info("========================================")
        logger.info("Starting command synchronization...")
        
        # Multi-stage synchronization with retries
        sync_success = False
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Global sync attempt {attempt}...")
                
                # Global sync
                global_synced = await bot.tree.sync()
                
                logger.info(f"✅ Global sync successful: {len(global_synced)} commands")
                logger.info(f"Synced commands: {', '.join([cmd.name for cmd in global_synced])}")
                
                # Verify critical commands
                critical_commands = ["show_union_leader", "show_union_detail"]
                for cmd_name in critical_commands:
                    if any(cmd.name == cmd_name for cmd in global_synced):
                        logger.info(f"  ✅ Critical command '{cmd_name}' synchronized")
                    else:
                        logger.warning(f"  ⚠️ Critical command '{cmd_name}' missing from sync")
                
                # Guild-specific sync for each guild
                for guild in bot.guilds:
                    try:
                        logger.info(f"Syncing to guild: {guild.name}")
                        
                        # Copy global commands to guild
                        bot.tree.clear_commands(guild=guild)
                        for cmd in global_synced:
                            bot.tree.add_command(cmd, guild=guild)
                        
                        guild_synced = await bot.tree.sync(guild=guild)
                        logger.info(f"✅ Guild sync: {len(guild_synced)} commands to {guild.name}")
                        
                    except Exception as guild_error:
                        logger.error(f"❌ Guild sync failed for {guild.name}: {str(guild_error)}")
                
                # Update status
                bot_status.commands_synced = len(global_synced)
                bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
                sync_success = True
                break
                
            except Exception as e:
                logger.error(f"❌ Sync attempt {attempt} failed: {str(e)}")
                bot_status.sync_errors += 1
                
                if attempt < max_retries:
                    logger.info(f"Retrying in 3 seconds... ({attempt}/{max_retries})")
                    await asyncio.sleep(3)
                else:
                    logger.error("❌ All sync attempts failed!")
        
        # Final status report
        logger.info("========================================")
        if sync_success:
            logger.info("🎉 BOT INITIALIZATION COMPLETE")
            logger.info(f"✅ {loaded_modules} modules loaded")
            logger.info(f"✅ {bot_status.commands_synced} commands synchronized")
            logger.info(f"✅ Connected to {len(bot.guilds)} guilds")
            logger.info("Commands will be available in Discord within 1-2 minutes")
        else:
            logger.warning("⚠️ BOT STARTED WITH SYNC ISSUES")
            logger.warning("Use !sync_commands to manually sync")
        
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
# ADMINISTRATIVE COMMANDS
# ============================================================

@bot.command(name='sync_commands')
async def sync_commands(ctx):
    """Manually sync commands to Discord (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🔄 **SYNCING COMMANDS...**")
        
        # Global sync
        synced = await bot.tree.sync()
        
        success_msg = f"""✅ **SYNC COMPLETE!**

**Commands synced:** {len(synced)}
**Status:** Commands will be available in 1-2 minutes

**Synced commands:**
{', '.join([f'`/{cmd.name}`' for cmd in synced[:10]])}
{'...' if len(synced) > 10 else ''}"""
        
        await ctx.send(success_msg)
        
        # Update status
        bot_status.commands_synced = len(synced)
        bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
        
        logger.info(f"Manual sync successful: {len(synced)} commands")
        
    except Exception as e:
        await ctx.send(f"❌ **Sync failed:** {str(e)}")
        logger.error(f"Manual sync error: {str(e)}")

@bot.command(name='force_guild_sync')
async def force_guild_sync(ctx):
    """Force sync all commands specifically to this guild (Admin only)"""
    # Check admin permissions
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🔄 **FORCE GUILD SYNC STARTING...**")
        
        # Get current guild
        guild = ctx.guild
        guild_id = guild.id
        
        logger.info(f"Force guild sync requested for: {guild.name} (ID: {guild_id})")
        
        # Clear guild-specific commands first
        bot.tree.clear_commands(guild=guild)
        logger.info("Cleared existing guild commands")
        
        # Copy all global commands to guild-specific
        global_commands = bot.tree.get_commands()
        for cmd in global_commands:
            bot.tree.add_command(cmd, guild=guild)
        
        logger.info(f"Added {len(global_commands)} commands to guild tree")
        
        # Sync specifically to this guild
        synced = await bot.tree.sync(guild=guild)
        
        success_msg = f"""🎉 **GUILD SYNC COMPLETE!**
        
✅ **Guild:** {guild.name}
✅ **Commands Synced:** {len(synced)}
✅ **Status:** Ready to use

**Commands now available:**
{', '.join([f'`/{cmd.name}`' for cmd in synced[:10]])}
{'...' if len(synced) > 10 else ''}

⏰ **Commands will appear in 1-2 minutes**
Try typing `/` to see them!"""
        
        await ctx.send(success_msg)
        
        logger.info(f"✅ Force guild sync successful: {len(synced)} commands to {guild.name}")
        logger.info(f"Synced commands: {[cmd.name for cmd in synced]}")
        
        # Update status
        bot_status.commands_synced = len(synced)
        bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
        
    except Exception as e:
        error_msg = f"❌ **Guild sync failed:** {str(e)}"
        await ctx.send(error_msg)
        logger.error(f"Force guild sync error: {str(e)}")
        logger.error(traceback.format_exc())

@bot.command(name='debug_commands')
async def debug_commands(ctx):
    """Debug command visibility (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        guild = ctx.guild
        
        # Get global commands
        global_commands = bot.tree.get_commands()
        
        # Get guild-specific commands
        guild_commands = bot.tree.get_commands(guild=guild)
        
        # Check if specific commands exist
        show_leader_global = any(cmd.name == "show_union_leader" for cmd in global_commands)
        show_leader_guild = any(cmd.name == "show_union_leader" for cmd in guild_commands)
        
        debug_info = f"""🔍 **COMMAND DEBUG INFO**

**Global Commands:** {len(global_commands)}
**Guild Commands:** {len(guild_commands)}

**show_union_leader status:**
- Global: {'✅ Found' if show_leader_global else '❌ Missing'}
- Guild: {'✅ Found' if show_leader_guild else '❌ Missing'}

**All Global Commands:**
{', '.join([f'`{cmd.name}`' for cmd in global_commands])}

**Guild Commands:**
{', '.join([f'`{cmd.name}`' for cmd in guild_commands]) if guild_commands else 'None'}

**Recommendation:**
{'✅ Commands should be visible' if show_leader_guild else '⚠️ Run !force_guild_sync'}"""

        await ctx.send(debug_info)
        
    except Exception as e:
        await ctx.send(f"❌ Debug failed: {str(e)}")

@bot.command(name='reload_module')
async def reload_module(ctx, module_name: str):
    """Reload a specific module (Admin only)"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send(f"🔄 **RELOADING MODULE:** `{module_name}`")
        
        # Reload the module
        full_module_name = f"cogs.{module_name}"
        await bot.reload_extension(full_module_name)
        
        await ctx.send(f"✅ **MODULE RELOADED:** `{module_name}`")
        logger.info(f"Module reloaded: {full_module_name}")
        
    except Exception as e:
        await ctx.send(f"❌ **Reload failed:** {str(e)}")
        logger.error(f"Module reload error: {str(e)}")

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
        total_commands = len(bot.tree.get_commands())
        
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
            value=f"""**Total Commands:** {total_commands}
**Last Sync:** {bot_status.commands_synced}
**Sync Errors:** {bot_status.sync_errors}""",
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

@bot.command(name='list_commands')
async def list_commands(ctx):
    """List all available commands organized by category"""
    try:
        commands_by_cog = {}
        
        # Organize commands by cog
        for cmd in bot.tree.get_commands():
            cog_name = getattr(cmd, 'binding', None)
            if cog_name:
                cog_name = cog_name.__class__.__name__
            else:
                cog_name = "General"
            
            if cog_name not in commands_by_cog:
                commands_by_cog[cog_name] = []
            commands_by_cog[cog_name].append(cmd)
        
        embed = discord.Embed(
            title="📋 Available Commands",
            description=f"Total Commands: {len(bot.tree.get_commands())}",
            color=discord.Color.blue()
        )
        
        for cog_name, commands in commands_by_cog.items():
            command_list = []
            for cmd in commands:
                command_list.append(f"`/{cmd.name}` - {cmd.description}")
            
            embed.add_field(
                name=f"📁 {cog_name} ({len(commands)})",
                value="\n".join(command_list),
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Failed to list commands: {str(e)}")

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
        embed = discord.Embed(
            title="🤖 Union Bot Information",
            description="Discord Union Management Bot",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👤 Bot", value=f"{bot.user.name}#{bot.user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=str(bot.user.id), inline=True)
        embed.add_field(name="🏠 Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="⚙️ Commands", value=str(len(bot.tree.get_commands())), inline=True)
        
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

@bot.command(name='test_slash')
async def test_slash(ctx):
    """Test if slash commands are working"""
    await ctx.send("✅ **Prefix commands work!** Now try `/ping` to test slash commands.")

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
        
        logger.info("Starting Discord Union Bot...")
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

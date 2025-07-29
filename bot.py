import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging
import datetime
import signal
import sys
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# ENHANCED LOGGING & PERFORMANCE MONITORING
# ============================================================

# Setup comprehensive logging with reduced discord.py verbosity
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Reduce discord.py logging noise
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ============================================================
# BOT CONFIGURATION & PERFORMANCE OPTIMIZATIONS
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()

# Create bot with optimized settings
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    heartbeat_timeout=60.0,  # Increase heartbeat timeout
    chunk_guilds_at_startup=False,  # Reduce startup load
    member_cache_flags=discord.MemberCacheFlags.none()  # Reduce memory usage
)

# Thread pool for blocking operations
executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="BotWorker")

# Bot status tracking
class BotStatus:
    def __init__(self):
        self.startup_time = None
        self.commands_synced = 0
        self.last_sync_time = None
        self.modules_loaded = 0
        self.sync_errors = 0
        self.heartbeat_warnings = 0

bot_status = BotStatus()

# ============================================================
# PERFORMANCE UTILITIES
# ============================================================

async def safe_blocking_operation(blocking_func, *args, **kwargs):
    """Run blocking operations in a thread pool to avoid blocking the event loop"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, blocking_func, *args, **kwargs)

def performance_monitor(func_name):
    """Decorator to monitor function execution time"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()
            try:
                result = await func(*args, **kwargs)
                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time
                
                if execution_time > 1.0:  # Log operations taking > 1 second
                    logger.warning(f"Slow operation '{func_name}' took {execution_time:.2f} seconds")
                elif execution_time > 5.0:  # Critical threshold
                    logger.error(f"CRITICAL: '{func_name}' blocked for {execution_time:.2f} seconds")
                    
                return result
            except Exception as e:
                end_time = asyncio.get_event_loop().time()
                execution_time = end_time - start_time
                logger.error(f"Error in '{func_name}' after {execution_time:.2f}s: {e}")
                raise
        return wrapper
    return decorator

# ============================================================
# BOT EVENT HANDLERS WITH PERFORMANCE MONITORING
# ============================================================

@bot.event
async def on_ready():
    """Optimized bot initialization with heartbeat protection"""
    try:
        # Set startup time
        bot_status.startup_time = datetime.datetime.now(datetime.timezone.utc)
        
        logger.info("============================================================")
        logger.info("DISCORD UNION BOT INITIALIZATION (PERFORMANCE OPTIMIZED)")
        logger.info("============================================================")
        logger.info(f"Bot: {bot.user.name}#{bot.user.discriminator} (ID: {bot.user.id})")
        logger.info(f"Connected to {len(bot.guilds)} guilds")
        
        # Log guild information efficiently
        for guild in bot.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
        
        # Clear existing commands to prevent duplicates
        logger.info("Clearing existing commands...")
        bot.tree.clear_commands(guild=None)
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
        
        # Short delay to prevent API rate limiting
        await asyncio.sleep(0.5)
        
        # Load command modules with error handling
        logger.info("Loading command modules...")
        modules = [
            "cogs.basic_commands",
            "cogs.union_management", 
            "cogs.union_membership",
            "cogs.union_info"
        ]
        
        loaded_modules = 0
        
        for module in modules:
            try:
                logger.info(f"Loading {module}...")
                await bot.load_extension(module)
                loaded_modules += 1
                # Small delay between module loads to prevent blocking
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to load {module}: {str(e)}")
                logger.error(traceback.format_exc())
        
        bot_status.modules_loaded = loaded_modules
        total_commands = len(bot.tree.get_commands())
        
        logger.info("========================================")
        logger.info("Module Loading Summary:")
        logger.info(f"  Successful: {loaded_modules}/{len(modules)}")
        logger.info(f"  Failed: {len(modules) - loaded_modules}")
        logger.info(f"  Total Commands: {total_commands}")
        
        if total_commands == 0:
            logger.error("❌ NO COMMANDS IN TREE - Critical Issue!")
            return
        
        # Critical command verification
        commands_in_tree = bot.tree.get_commands()
        critical_commands = ["show_union_leader", "show_union_detail"]
        
        logger.info("Critical command check:")
        for critical_cmd in critical_commands:
            if any(cmd.name == critical_cmd for cmd in commands_in_tree):
                logger.info(f"  ✅ {critical_cmd} loaded successfully")
            else:
                logger.warning(f"  ⚠️ {critical_cmd} missing from tree")
        
        # Optimized guild-specific synchronization
        logger.info("Starting optimized command synchronization...")
        sync_success_count = 0
        
        for guild in bot.guilds:
            try:
                logger.info(f"Syncing to guild: {guild.name}")
                
                # Copy commands to guild tree (no global commands)
                bot.tree.clear_commands(guild=guild)
                for cmd in commands_in_tree:
                    bot.tree.add_command(cmd, guild=guild)
                
                # Sync with timeout protection
                synced = await asyncio.wait_for(
                    bot.tree.sync(guild=guild), 
                    timeout=30.0
                )
                
                sync_success_count += 1
                bot_status.commands_synced = len(synced)
                bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
                
                logger.info(f"✅ Synced {len(synced)} commands to {guild.name}")
                
                # Verify critical commands in sync result
                synced_names = [cmd.name for cmd in synced]
                for critical_cmd in critical_commands:
                    if critical_cmd in synced_names:
                        logger.info(f"  ✅ {critical_cmd} available in {guild.name}")
                    else:
                        logger.warning(f"  ⚠️ {critical_cmd} missing in {guild.name}")
                
                # Small delay between guild syncs to prevent rate limiting
                await asyncio.sleep(1.0)
                
            except asyncio.TimeoutError:
                logger.error(f"Sync timeout for guild: {guild.name}")
                bot_status.sync_errors += 1
            except Exception as e:
                logger.error(f"Sync failed for {guild.name}: {str(e)}")
                bot_status.sync_errors += 1
        
        # Final status report
        logger.info("========================================")
        if sync_success_count > 0:
            logger.info("🎉 BOT INITIALIZATION COMPLETE")
            logger.info(f"✅ {loaded_modules} modules loaded")
            logger.info(f"✅ {bot_status.commands_synced} commands per guild")
            logger.info(f"✅ Synced to {sync_success_count}/{len(bot.guilds)} guilds")
            logger.info("✅ Heartbeat optimization enabled")
            
            if bot_status.sync_errors > 0:
                logger.warning(f"⚠️ {bot_status.sync_errors} sync errors occurred")
            
            logger.info("Commands will be available in Discord within 1-2 minutes")
        else:
            logger.error("❌ CRITICAL: No successful synchronizations")
        
        logger.info("============================================================")
        
        # Start background tasks
        asyncio.create_task(heartbeat_monitor())
        
    except Exception as e:
        logger.error(f"Critical error during bot initialization: {str(e)}")
        logger.error(traceback.format_exc())

@bot.event
async def on_disconnect():
    """Enhanced disconnect handling"""
    logger.warning("Bot disconnected from Discord")

@bot.event
async def on_resumed():
    """Enhanced resume handling"""
    logger.info("Bot resumed connection to Discord")

@bot.event
async def on_command_error(ctx, error):
    """Enhanced error handling with performance logging"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    
    else:
        # Log unexpected errors with context
        logger.error(f"Command error in {ctx.command}: {str(error)}")
        logger.error(f"User: {ctx.author} | Channel: {ctx.channel} | Guild: {ctx.guild}")
        logger.error(traceback.format_exc())
        await ctx.send(f"❌ An unexpected error occurred: {str(error)}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    """Global error handler for slash commands with performance monitoring"""
    if isinstance(error, discord.app_commands.CommandNotFound):
        logger.error(f"Command not found: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Command not found. This may indicate a synchronization issue. "
                "Please contact an administrator.", 
                ephemeral=True
            )
    elif isinstance(error, discord.app_commands.CommandOnCooldown):
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Command on cooldown. Try again in {error.retry_after:.1f} seconds.", 
                ephemeral=True
            )
    else:
        logger.error(f"App command error: {error}")
        logger.error(f"Command: {interaction.command} | User: {interaction.user} | Guild: {interaction.guild}")
        logger.error(traceback.format_exc())
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An unexpected error occurred. The issue has been logged.", 
                ephemeral=True
            )

# ============================================================
# BACKGROUND TASKS & MONITORING
# ============================================================

async def heartbeat_monitor():
    """Background task to monitor bot health and performance"""
    await bot.wait_until_ready()
    logger.info("🔄 Heartbeat monitor started")
    
    last_heartbeat_warning = 0
    
    while not bot.is_closed():
        try:
            # Check heartbeat latency
            latency = bot.latency * 1000  # Convert to milliseconds
            
            if latency > 1000:  # More than 1 second
                bot_status.heartbeat_warnings += 1
                current_time = asyncio.get_event_loop().time()
                
                # Rate limit heartbeat warnings (max 1 per minute)
                if current_time - last_heartbeat_warning > 60:
                    logger.warning(f"High latency detected: {latency:.1f}ms")
                    last_heartbeat_warning = current_time
            
            # Memory cleanup every hour
            if bot_status.startup_time:
                uptime = datetime.datetime.now(datetime.timezone.utc) - bot_status.startup_time
                if uptime.total_seconds() % 3600 < 30:  # Every hour (with 30s window)
                    logger.debug("Performing periodic cleanup")
                    # Force garbage collection
                    import gc
                    gc.collect()
            
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Heartbeat monitor error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

# ============================================================
# OPTIMIZED SYNC COMMANDS
# ============================================================

@bot.command(name='force_sync')
@performance_monitor('force_sync')
async def force_sync(ctx):
    """Force guild registration and sync (Admin only) - Optimized"""
    if not any(role.name.lower() in ["admin", "administrator"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator permissions.")
        return
    
    try:
        await ctx.send("🔄 **OPTIMIZED FORCE SYNC STARTING...**")
        
        guild = ctx.guild
        
        # Step 1: Clear and rebuild command tree
        await ctx.send("📍 **Step 1: Rebuilding command tree...**")
        bot.tree.clear_commands(guild=guild)
        
        # Get global commands and copy to guild
        global_commands = bot.tree.get_commands()
        for cmd in global_commands:
            bot.tree.add_command(cmd, guild=guild)
        
        guild_commands = len(bot.tree.get_commands(guild=guild))
        await ctx.send(f"📊 **Commands ready:** {guild_commands}")
        
        # Step 2: Sync with timeout protection
        await ctx.send("📍 **Step 2: Syncing to Discord...**")
        
        try:
            synced = await asyncio.wait_for(
                bot.tree.sync(guild=guild), 
                timeout=30.0
            )
        except asyncio.TimeoutError:
            await ctx.send("❌ **Sync timeout.** Discord may be experiencing delays. Try again in a few minutes.")
            return
        
        success_msg = f"""✅ **OPTIMIZED SYNC COMPLETE!**

🎯 **Guild:** {guild.name}
✅ **Commands Synced:** {len(synced)}
🚀 **Performance:** Optimized for reduced blocking

**Available commands:**
{', '.join([f'`/{cmd.name}`' for cmd in synced[:10]])}
{'...' if len(synced) > 10 else ''}

⏰ **Commands will appear in 1-2 minutes**"""
        
        await ctx.send(success_msg)
        
        # Update status
        bot_status.commands_synced = len(synced)
        bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
        
        logger.info(f"✅ Force sync successful: {len(synced)} commands to {guild.name}")
        
    except Exception as e:
        error_msg = f"❌ **Force sync failed:** {str(e)}"
        await ctx.send(error_msg)
        logger.error(f"Force sync error: {str(e)}")
        logger.error(traceback.format_exc())

@bot.command(name='bot_health')
async def bot_health(ctx):
    """Display bot health and performance statistics"""
    try:
        uptime = datetime.datetime.now(datetime.timezone.utc) - bot_status.startup_time if bot_status.startup_time else datetime.timedelta(0)
        latency = round(bot.latency * 1000, 1)
        
        # Health status
        health_color = discord.Color.green()
        health_status = "🟢 Healthy"
        
        if latency > 1000:
            health_color = discord.Color.orange()
            health_status = "🟡 High Latency"
        
        if bot_status.heartbeat_warnings > 10:
            health_color = discord.Color.red()
            health_status = "🔴 Performance Issues"
        
        embed = discord.Embed(
            title="🤖 Bot Health Status",
            description=health_status,
            color=health_color
        )
        
        embed.add_field(name="📊 Performance", value=f"Latency: {latency}ms\nUptime: {str(uptime).split('.')[0]}", inline=True)
        embed.add_field(name="⚙️ Commands", value=f"Synced: {bot_status.commands_synced}\nModules: {bot_status.modules_loaded}", inline=True)
        embed.add_field(name="⚠️ Warnings", value=f"Heartbeat: {bot_status.heartbeat_warnings}\nSync Errors: {bot_status.sync_errors}", inline=True)
        embed.add_field(name="🏠 Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="📈 Memory", value=f"Threads: {executor._threads if hasattr(executor, '_threads') else 'N/A'}", inline=True)
        embed.add_field(name="🔄 Last Sync", value=f"{bot_status.last_sync_time.strftime('%H:%M:%S UTC') if bot_status.last_sync_time else 'Never'}", inline=True)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Health check failed: {str(e)}")

# ============================================================
# BASIC SLASH COMMANDS (Performance Optimized)
# ============================================================

@bot.tree.command(name="ping", description="Test bot responsiveness and performance")
async def ping(interaction: discord.Interaction):
    """Optimized ping command with performance metrics"""
    try:
        # Measure response time
        start_time = asyncio.get_event_loop().time()
        
        latency = round(bot.latency * 1000, 1)
        
        # Calculate command processing time
        processing_time = round((asyncio.get_event_loop().time() - start_time) * 1000, 1)
        
        # Health indicator
        if latency < 100:
            status = "🟢 Excellent"
        elif latency < 300:
            status = "🟡 Good"
        elif latency < 1000:
            status = "🟠 Fair"
        else:
            status = "🔴 Poor"
        
        await interaction.response.send_message(
            f"🏓 **Pong!**\n"
            f"**WebSocket:** {latency}ms\n"
            f"**Processing:** {processing_time}ms\n"
            f"**Status:** {status}"
        )
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Ping failed: {str(e)}", ephemeral=True)

@bot.tree.command(name="bot_info", description="Display optimized bot information")
async def bot_info(interaction: discord.Interaction):
    """Display comprehensive bot information"""
    try:
        guild = interaction.guild
        uptime = datetime.datetime.now(datetime.timezone.utc) - bot_status.startup_time if bot_status.startup_time else datetime.timedelta(0)
        
        embed = discord.Embed(
            title="🤖 Union Bot Information",
            description="Discord Union Management Bot - Performance Optimized",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="👤 Bot", value=f"{bot.user.name}#{bot.user.discriminator}", inline=True)
        embed.add_field(name="🆔 ID", value=str(bot.user.id), inline=True)
        embed.add_field(name="⏱️ Uptime", value=str(uptime).split('.')[0], inline=True)
        embed.add_field(name="🏠 Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="⚙️ Commands", value=str(bot_status.commands_synced), inline=True)
        embed.add_field(name="🧩 Modules", value=str(bot_status.modules_loaded), inline=True)
        embed.add_field(name="🔄 Performance", value="✅ Optimized" if bot_status.heartbeat_warnings < 5 else "⚠️ Degraded", inline=True)
        embed.add_field(name="📊 Latency", value=f"{round(bot.latency * 1000, 1)}ms", inline=True)
        embed.add_field(name="🎯 Status", value="🟢 Operational", inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Info display failed: {str(e)}", ephemeral=True)

# ============================================================
# GRACEFUL SHUTDOWN HANDLING
# ============================================================

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    logger.info('Shutting down bot gracefully...')
    
    # Close thread pool
    executor.shutdown(wait=False)
    
    # Close bot connection
    asyncio.create_task(bot.close())
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================
# MAIN STARTUP FUNCTION
# ============================================================

@performance_monitor('main_startup')
async def main():
    """Optimized main bot startup function"""
    try:
        if not TOKEN:
            logger.error("❌ DISCORD_TOKEN environment variable not found!")
            logger.error("Please set your bot token in the .env file")
            return
        
        logger.info("Starting Discord Union Bot (Performance Optimized)...")
        logger.info("Optimizations: Heartbeat monitoring, thread pooling, reduced blocking")
        
        # Initialize bot with connection retry logic
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                await bot.start(TOKEN)
                break
            except discord.ConnectionClosed:
                logger.warning(f"Connection closed, attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    raise
            except discord.HTTPException as e:
                logger.error(f"HTTP Exception on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
        
    except discord.LoginFailure:
        logger.error("❌ Invalid Discord token!")
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup thread pool
        executor.shutdown(wait=True)

# ============================================================
# STARTUP EXECUTION
# ============================================================

if __name__ == "__main__":
    try:
        # Set up asyncio policies for better performance on Windows
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical startup error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("Bot shutdown complete")

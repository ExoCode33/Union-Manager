import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging

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

# Suppress Discord.py noise
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)

# Bot configuration
TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

class BotStatus:
    """Track bot status and statistics"""
    def __init__(self):
        self.startup_time = None
        self.commands_synced = 0
        self.modules_loaded = 0
        self.last_sync_time = None

bot_status = BotStatus()

@bot.event
async def on_ready():
    import datetime
    bot_status.startup_time = datetime.datetime.now(datetime.timezone.utc)
    
    logger.info("=" * 60)
    logger.info("DISCORD UNION BOT INITIALIZATION")
    logger.info("=" * 60)
    logger.info(f"Bot: {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Log detailed guild information
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
        
        # Check bot permissions in each guild
        bot_member = guild.get_member(bot.user.id)
        if bot_member:
            perms = bot_member.guild_permissions
            logger.info(f"    Permissions: Admin={perms.administrator}, SendMessages={perms.send_messages}")
    
    # Clear existing command state for clean initialization
    logger.info("Clearing existing command state...")
    bot.tree.clear_commands(guild=None)
    
    # Small delay to ensure Discord processes the clear
    await asyncio.sleep(2)
    
    # Load all command modules
    cog_modules = [
        ("cogs.basic_commands", "BasicCommands"),
        ("cogs.union_management", "UnionManagement"),
        ("cogs.union_membership", "UnionMembership"),
        ("cogs.union_info", "UnionInfo")
    ]
    
    loaded_modules = []
    failed_modules = []
    total_commands = 0
    
    logger.info("Loading command modules...")
    for module_path, cog_class_name in cog_modules:
        try:
            logger.info(f"Loading {module_path}...")
            
            # Load the extension
            await bot.load_extension(module_path)
            
            # Verify the cog loaded correctly
            cog = bot.get_cog(cog_class_name)
            if cog:
                commands = cog.get_app_commands()
                command_count = len(commands)
                total_commands += command_count
                
                logger.info(f"  ✅ {module_path}: {command_count} commands loaded")
                
                # Log each command for verification
                for cmd in commands:
                    logger.debug(f"    - {cmd.name}: {cmd.description}")
                
                loaded_modules.append(module_path)
            else:
                logger.error(f"  ❌ {module_path}: Cog class '{cog_class_name}' not found")
                failed_modules.append(module_path)
                
        except Exception as e:
            logger.error(f"  ❌ {module_path}: Failed to load - {str(e)}")
            logger.debug(f"  Error details: {traceback.format_exc()}")
            failed_modules.append(module_path)
    
    # Module loading summary
    bot_status.modules_loaded = len(loaded_modules)
    logger.info("=" * 40)
    logger.info(f"Module Loading Summary:")
    logger.info(f"  Successful: {len(loaded_modules)}/{len(cog_modules)}")
    logger.info(f"  Failed: {len(failed_modules)}")
    logger.info(f"  Total Commands: {total_commands}")
    
    if failed_modules:
        logger.warning(f"  Failed Modules: {', '.join(failed_modules)}")
    
    # Verify commands are in the tree
    tree_commands = bot.tree.get_commands()
    logger.info(f"Commands in tree: {len(tree_commands)}")
    
    if len(tree_commands) == 0:
        logger.error("CRITICAL: No commands in tree - bot will not function")
        return
    
    # Log all commands ready for sync
    logger.info("Commands ready for synchronization:")
    for cmd in tree_commands:
        logger.info(f"  - {cmd.name}: {cmd.description}")
    
    # Multi-stage synchronization process
    logger.info("=" * 40)
    logger.info("Starting command synchronization...")
    
    sync_successful = False
    
    # Stage 1: Global sync
    for attempt in range(1, 4):  # Try 3 times
        try:
            logger.info(f"Global sync attempt {attempt}...")
            synced_commands = await bot.tree.sync()
            
            logger.info(f"✅ Global sync successful: {len(synced_commands)} commands")
            bot_status.commands_synced = len(synced_commands)
            bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
            
            # Log synchronized command names
            if synced_commands:
                synced_names = [cmd.name for cmd in synced_commands]
                logger.info(f"Synced commands: {', '.join(synced_names)}")
                
                # Verify critical commands
                critical_commands = ["show_union_leader", "show_union_detail"]
                for critical_cmd in critical_commands:
                    if critical_cmd in synced_names:
                        logger.info(f"  ✅ Critical command '{critical_cmd}' synchronized")
                    else:
                        logger.warning(f"  ⚠️ Critical command '{critical_cmd}' missing")
                
                sync_successful = True
                break
            else:
                logger.warning(f"No commands synchronized on attempt {attempt}")
                
        except discord.HTTPException as e:
            logger.error(f"HTTP error during global sync attempt {attempt}: {e}")
            if attempt < 3:
                wait_time = attempt * 3
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error during sync attempt {attempt}: {e}")
            if attempt < 3:
                await asyncio.sleep(2)
    
    # Stage 2: Guild-specific sync for each guild
    if sync_successful:
        for guild in bot.guilds:
            try:
                logger.info(f"Syncing to guild: {guild.name}")
                guild_synced = await bot.tree.sync(guild=guild)
                logger.info(f"✅ Guild sync: {len(guild_synced)} commands to {guild.name}")
            except Exception as e:
                logger.error(f"❌ Guild sync failed for {guild.name}: {e}")
    
    # Final status report
    logger.info("=" * 40)
    if sync_successful:
        logger.info("🎉 BOT INITIALIZATION COMPLETE")
        logger.info(f"✅ {bot_status.modules_loaded} modules loaded")
        logger.info(f"✅ {bot_status.commands_synced} commands synchronized")
        logger.info(f"✅ Connected to {len(bot.guilds)} guilds")
        logger.info("Commands will be available in Discord within 1-2 minutes")
    else:
        logger.error("❌ BOT INITIALIZATION FAILED")
        logger.error("Commands may not be available in Discord")
    logger.info("=" * 60)

@bot.event
async def on_guild_join(guild):
    """Handle bot joining new guilds"""
    logger.info(f"Joined new guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
    
    # Automatically sync commands to new guild
    try:
        synced = await bot.tree.sync(guild=guild)
        logger.info(f"Auto-synced {len(synced)} commands to new guild {guild.name}")
    except Exception as e:
        logger.error(f"Failed to auto-sync to new guild {guild.name}: {e}")

@bot.event
async def on_guild_remove(guild):
    """Handle bot leaving guilds"""
    logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    command_name = interaction.data.get('name', 'unknown') if interaction.data else 'unknown'
    user = f"{interaction.user.name} ({interaction.user.id})"
    guild = f"{interaction.guild.name} ({interaction.guild.id})" if interaction.guild else "DM"
    
    logger.error(f"Command error: /{command_name} by {user} in {guild}")
    logger.error(f"Error details: {str(error)}")
    logger.debug(f"Full traceback: {traceback.format_exc()}")
    
    # Send user-friendly error message
    error_message = "❌ An error occurred while processing your command. Please try again later."
    
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(error_message, ephemeral=True)
        else:
            await interaction.followup.send(error_message, ephemeral=True)
    except Exception as followup_error:
        logger.error(f"Failed to send error message to user: {followup_error}")

@bot.event
async def on_command_error(ctx, error):
    """Handle prefix command errors"""
    logger.error(f"Prefix command error: {ctx.command} by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}")
    logger.error(f"Error: {str(error)}")

# ============================================================================
# ADMINISTRATIVE COMMANDS
# ============================================================================

@bot.command(name='sync_commands')
async def sync_commands(ctx):
    """Manually synchronize slash commands (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    logger.info(f"Manual sync requested by {ctx.author} in {ctx.guild.name}")
    
    async with ctx.typing():
        try:
            # Global sync
            await ctx.send("🔄 Synchronizing commands globally...")
            global_synced = await bot.tree.sync()
            
            # Guild sync
            await ctx.send("🔄 Synchronizing commands to this guild...")
            guild_synced = await bot.tree.sync(guild=ctx.guild)
            
            # Update status
            import datetime
            bot_status.commands_synced = len(global_synced)
            bot_status.last_sync_time = datetime.datetime.now(datetime.timezone.utc)
            
            embed = discord.Embed(
                title="✅ Command Synchronization Complete",
                color=0x00FF00,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Global Sync", value=f"{len(global_synced)} commands", inline=True)
            embed.add_field(name="Guild Sync", value=f"{len(guild_synced)} commands", inline=True)
            embed.add_field(name="Status", value="Commands available in 1-2 minutes", inline=False)
            
            await ctx.send(embed=embed)
            logger.info(f"Manual sync completed: {len(global_synced)} global, {len(guild_synced)} guild")
            
        except Exception as e:
            await ctx.send(f"❌ Synchronization failed: {str(e)}")
            logger.error(f"Manual sync failed: {str(e)}")

@bot.command(name='guild_sync')
async def guild_sync(ctx):
    """Force sync commands to current guild specifically (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    logger.info(f"Guild-specific sync requested by {ctx.author} in {ctx.guild.name}")
    
    async with ctx.typing():
        try:
            synced = await bot.tree.sync(guild=ctx.guild)
            
            embed = discord.Embed(
                title="✅ Guild Synchronization Complete",
                description=f"Synchronized {len(synced)} commands to **{ctx.guild.name}**",
                color=0x00FF00,
                timestamp=discord.utils.utcnow()
            )
            
            if synced:
                command_list = ", ".join([cmd.name for cmd in synced[:10]])
                if len(synced) > 10:
                    command_list += f" ... and {len(synced) - 10} more"
                embed.add_field(name="Commands", value=command_list, inline=False)
            
            await ctx.send(embed=embed)
            logger.info(f"Guild sync completed: {len(synced)} commands to {ctx.guild.name}")
            
        except Exception as e:
            await ctx.send(f"❌ Guild synchronization failed: {str(e)}")
            logger.error(f"Guild sync failed: {str(e)}")

@bot.command(name='force_refresh')
async def force_refresh(ctx):
    """Complete command refresh - clear and re-sync everything (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    logger.info(f"Force refresh requested by {ctx.author} in {ctx.guild.name}")
    
    async with ctx.typing():
        try:
            # Step 1: Clear all commands
            await ctx.send("🔄 Step 1: Clearing all commands...")
            bot.tree.clear_commands(guild=None)
            await bot.tree.sync()
            
            # Step 2: Wait for Discord to process
            await ctx.send("⏳ Step 2: Waiting for Discord to process...")
            await asyncio.sleep(5)
            
            # Step 3: Re-sync globally
            await ctx.send("🔄 Step 3: Re-synchronizing globally...")
            global_synced = await bot.tree.sync()
            
            # Step 4: Sync to current guild
            await ctx.send("🔄 Step 4: Synchronizing to this guild...")
            guild_synced = await bot.tree.sync(guild=ctx.guild)
            
            # Final result
            embed = discord.Embed(
                title="✅ Complete Refresh Successful",
                color=0x00FF00,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Global Commands", value=str(len(global_synced)), inline=True)
            embed.add_field(name="Guild Commands", value=str(len(guild_synced)), inline=True)
            embed.add_field(name="⏰ Availability", value="Commands will appear in 2-3 minutes", inline=False)
            
            await ctx.send(embed=embed)
            logger.info(f"Force refresh completed: {len(global_synced)} global, {len(guild_synced)} guild")
            
        except Exception as e:
            await ctx.send(f"❌ Force refresh failed: {str(e)}")
            logger.error(f"Force refresh failed: {str(e)}")

@bot.command(name='reload_module')
async def reload_module(ctx, module_name: str = None):
    """Reload a specific command module (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    if not module_name:
        await ctx.send("❌ Please specify a module: `basic_commands`, `union_management`, `union_membership`, or `union_info`")
        return
    
    module_path = f"cogs.{module_name}"
    
    async with ctx.typing():
        try:
            # Unload the module
            await bot.unload_extension(module_path)
            await ctx.send(f"🔄 Unloaded {module_path}")
            
            # Reload the module
            await bot.load_extension(module_path)
            await ctx.send(f"✅ Reloaded {module_path}")
            
            # Sync commands
            synced = await bot.tree.sync()
            
            embed = discord.Embed(
                title="✅ Module Reload Complete",
                description=f"Successfully reloaded **{module_path}**",
                color=0x00FF00
            )
            embed.add_field(name="Commands Synced", value=str(len(synced)), inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Module {module_path} reloaded by {ctx.author}")
            
        except Exception as e:
            await ctx.send(f"❌ Failed to reload {module_path}: {str(e)}")
            logger.error(f"Failed to reload {module_path}: {str(e)}")

@bot.command(name='bot_status')
async def bot_status(ctx):
    """Display comprehensive bot status information"""
    import datetime
    
    # Calculate uptime
    uptime = "Unknown"
    if bot_status.startup_time:
        uptime_delta = datetime.datetime.now(datetime.timezone.utc) - bot_status.startup_time
        hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        uptime = f"{hours}h {minutes}m"
    
    # Last sync time
    last_sync = "Never"
    if bot_status.last_sync_time:
        sync_delta = datetime.datetime.now(datetime.timezone.utc) - bot_status.last_sync_time
        if sync_delta.total_seconds() < 60:
            last_sync = "Just now"
        elif sync_delta.total_seconds() < 3600:
            last_sync = f"{int(sync_delta.total_seconds() // 60)}m ago"
        else:
            last_sync = f"{int(sync_delta.total_seconds() // 3600)}h ago"
    
    embed = discord.Embed(
        title="🤖 Union Bot Status",
        color=0x00FF00,
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"**Commands:** {len(bot.tree.get_commands())}\n"
              f"**Modules:** {len(bot.cogs)}\n"
              f"**Guilds:** {len(bot.guilds)}\n"
              f"**Users:** {sum(guild.member_count for guild in bot.guilds)}",
        inline=True
    )
    
    embed.add_field(
        name="🔧 System",
        value=f"**Uptime:** {uptime}\n"
              f"**Latency:** {round(bot.latency * 1000)}ms\n"
              f"**Last Sync:** {last_sync}\n"
              f"**Status:** 🟢 Online",
        inline=True
    )
    
    # List loaded modules
    if bot.cogs:
        module_list = []
        for cog_name, cog in bot.cogs.items():
            cmd_count = len(cog.get_app_commands())
            module_list.append(f"**{cog_name}:** {cmd_count} commands")
        
        embed.add_field(
            name="📦 Loaded Modules",
            value="\n".join(module_list),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='list_commands')
async def list_commands(ctx):
    """List all available slash commands organized by category"""
    commands = bot.tree.get_commands()
    
    if not commands:
        await ctx.send("❌ No commands are currently loaded.")
        return
    
    embed = discord.Embed(
        title="📋 Available Commands",
        description=f"Total: **{len(commands)}** commands",
        color=0x0099FF
    )
    
    # Group commands by cog/category
    command_groups = {
        "Basic Commands": [],
        "Union Management": [],
        "Union Membership": [],
        "Union Information": []
    }
    
    for cmd in commands:
        cmd_text = f"`/{cmd.name}` - {cmd.description[:50]}{'...' if len(cmd.description) > 50 else ''}"
        
        # Categorize based on command name patterns
        if any(x in cmd.name for x in ['register', 'deregister', 'search']):
            command_groups["Basic Commands"].append(cmd_text)
        elif any(x in cmd.name for x in ['role_as_union', 'union_leader']):
            command_groups["Union Management"].append(cmd_text)
        elif any(x in cmd.name for x in ['add_user', 'remove_user']):
            command_groups["Union Membership"].append(cmd_text)
        elif any(x in cmd.name for x in ['show_union', 'union_detail']):
            command_groups["Union Information"].append(cmd_text)
        else:
            command_groups["Basic Commands"].append(cmd_text)
    
    # Add fields for each category
    for category, category_commands in command_groups.items():
        if category_commands:
            # Split long lists to avoid embed limits
            for i in range(0, len(category_commands), 8):
                chunk = category_commands[i:i+8]
                field_name = category if i == 0 else f"{category} (cont.)"
                embed.add_field(
                    name=f"📁 {field_name}",
                    value="\n".join(chunk),
                    inline=False
                )
    
    await ctx.send(embed=embed)

# ============================================================================
# UTILITY COMMANDS
# ============================================================================

@bot.command(name='ping')
async def ping_prefix(ctx):
    """Test bot responsiveness using prefix command"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="ping", description="Test bot responsiveness")
async def ping_slash(interaction: discord.Interaction):
    """Test bot responsiveness using slash command"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms", ephemeral=True)

@bot.tree.command(name="bot_info", description="Display bot information")
async def bot_info_slash(interaction: discord.Interaction):
    """Display bot information via slash command"""
    embed = discord.Embed(
        title="🤖 Union Manager Bot",
        description="Professional Discord bot for managing gaming unions",
        color=0x7B68EE
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"**Commands:** {len(bot.tree.get_commands())}\n"
              f"**Guilds:** {len(bot.guilds)}\n"
              f"**Latency:** {round(bot.latency * 1000)}ms",
        inline=True
    )
    
    embed.add_field(
        name="🛠️ Features",
        value="• Dual IGN Management\n• Union Role System\n• Member Tracking\n• Auto Cleanup",
        inline=True
    )
    
    embed.set_footer(text="Use /help to see all available commands")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to run the bot with proper error handling"""
    if not TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        print("❌ ERROR: DISCORD_TOKEN environment variable not set")
        print("Please add your bot token to the environment variables.")
        return
    
    try:
        logger.info("Starting Discord Union Bot...")
        bot.run(TOKEN)
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user interrupt")
        print("\n👋 Bot stopped by user")
        
    except discord.LoginFailure:
        logger.error("Invalid bot token provided")
        print("❌ ERROR: Invalid bot token")
        print("Please check your DISCORD_TOKEN environment variable.")
        
    except discord.PrivilegedIntentsRequired:
        logger.error("Bot missing required privileged intents")
        print("❌ ERROR: Missing privileged intents")
        print("Please enable all intents in the Discord Developer Portal.")
        
    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        print(f"❌ FATAL ERROR: {str(e)}")
        print("Check bot.log for detailed error information.")

if __name__ == "__main__":
    main()

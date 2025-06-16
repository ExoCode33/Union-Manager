import discord
from discord.ext import commands
import os
import traceback
import asyncio
import logging

# Setup logging
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

@bot.event
async def on_ready():
    logger.info(f"Bot initialized: {bot.user} (ID: {bot.user.id})")
    logger.info(f"Connected to {len(bot.guilds)} guilds")
    
    # Log guild information
    for guild in bot.guilds:
        logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
    
    # Clear existing commands to ensure clean state
    logger.info("Clearing existing commands...")
    bot.tree.clear_commands(guild=None)
    
    # Brief pause to ensure Discord processes the clear
    await asyncio.sleep(2)
    
    # Load command modules
    cog_modules = [
        "cogs.basic_commands",
        "cogs.union_management", 
        "cogs.union_membership",
        "cogs.union_info"
    ]
    
    loaded_cogs = []
    failed_cogs = []
    total_commands = 0
    
    logger.info("Loading command modules...")
    for module in cog_modules:
        try:
            logger.info(f"Loading {module}...")
            await bot.load_extension(module)
            
            # Verify successful loading and count commands
            cog_name_map = {
                "cogs.basic_commands": "BasicCommands",
                "cogs.union_management": "UnionManagement",
                "cogs.union_membership": "UnionMembership", 
                "cogs.union_info": "UnionInfo"
            }
            
            cog = bot.get_cog(cog_name_map[module])
            if cog:
                commands = cog.get_app_commands()
                command_count = len(commands)
                total_commands += command_count
                
                logger.info(f"  Successfully loaded {command_count} commands from {module}")
                for cmd in commands:
                    logger.debug(f"    - {cmd.name}: {cmd.description}")
                
                loaded_cogs.append(module)
            else:
                logger.error(f"  Failed to retrieve cog object for {module}")
                failed_cogs.append(module)
                
        except Exception as e:
            logger.error(f"  Failed to load {module}: {str(e)}")
            logger.debug(f"  Error details: {traceback.format_exc()}")
            failed_cogs.append(module)
    
    # Summary of module loading
    logger.info(f"Module loading complete: {len(loaded_cogs)}/{len(cog_modules)} successful")
    logger.info(f"Total commands registered: {total_commands}")
    
    if failed_cogs:
        logger.warning(f"Failed modules: {', '.join(failed_cogs)}")
    
    # Verify commands are in tree
    tree_command_count = len(bot.tree.get_commands())
    logger.info(f"Commands in command tree: {tree_command_count}")
    
    if tree_command_count == 0:
        logger.error("No commands found in command tree - bot will not function properly")
        return
    
    # List all commands that will be synced
    logger.info("Commands ready for synchronization:")
    for cmd in bot.tree.get_commands():
        logger.info(f"  - {cmd.name}: {cmd.description}")
    
    # Synchronize commands with Discord
    logger.info("Synchronizing commands with Discord...")
    
    max_sync_attempts = 3
    sync_successful = False
    
    for attempt in range(1, max_sync_attempts + 1):
        try:
            synced_commands = await bot.tree.sync()
            logger.info(f"Successfully synchronized {len(synced_commands)} commands (attempt {attempt})")
            
            # Log synchronized command names
            if synced_commands:
                synced_names = [cmd.name for cmd in synced_commands]
                logger.info(f"Synchronized commands: {', '.join(synced_names)}")
                
                # Verify critical commands are present
                critical_commands = ["show_union_leader", "show_union_detail"]
                for critical_cmd in critical_commands:
                    if critical_cmd in synced_names:
                        logger.info(f"  ✓ Critical command '{critical_cmd}' synchronized successfully")
                    else:
                        logger.warning(f"  ! Critical command '{critical_cmd}' not found in sync")
                
                sync_successful = True
                break
            else:
                logger.warning(f"No commands synchronized on attempt {attempt}")
                
        except discord.HTTPException as e:
            logger.error(f"HTTP error during sync attempt {attempt}: {e}")
            if attempt < max_sync_attempts:
                wait_time = attempt * 2
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Unexpected error during sync attempt {attempt}: {e}")
            if attempt < max_sync_attempts:
                await asyncio.sleep(2)
    
    if sync_successful:
        logger.info("Bot initialization completed successfully")
        logger.info("Commands will be available in Discord within 1-2 minutes")
    else:
        logger.error("Failed to synchronize commands after all attempts")
        logger.error("Bot may not function properly")

@bot.event
async def on_guild_join(guild):
    """Log when bot joins a new guild"""
    logger.info(f"Joined guild: {guild.name} (ID: {guild.id}, Members: {guild.member_count})")

@bot.event
async def on_guild_remove(guild):
    """Log when bot leaves a guild"""
    logger.info(f"Left guild: {guild.name} (ID: {guild.id})")

@bot.event
async def on_application_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    """Handle application command errors"""
    command_name = interaction.data.get('name', 'unknown') if interaction.data else 'unknown'
    logger.error(f"Application command error in '{command_name}': {str(error)}")
    
    # Send user-friendly error message
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ An error occurred while processing your command. Please try again later.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ An error occurred while processing your command. Please try again later.",
                ephemeral=True
            )
    except Exception as followup_error:
        logger.error(f"Failed to send error message to user: {followup_error}")

# Administrative commands for bot management
@bot.command(name='sync_commands')
async def sync_commands(ctx):
    """Manually synchronize slash commands (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    logger.info(f"Manual command sync requested by {ctx.author} in {ctx.guild.name}")
    await ctx.send("🔄 Synchronizing commands...")
    
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"✅ Successfully synchronized {len(synced)} commands")
        logger.info(f"Manual sync completed: {len(synced)} commands synchronized")
        
        if synced:
            command_names = [cmd.name for cmd in synced]
            logger.info(f"Synchronized commands: {', '.join(command_names)}")
            
    except Exception as e:
        await ctx.send(f"❌ Synchronization failed: {str(e)}")
        logger.error(f"Manual sync failed: {str(e)}")

@bot.command(name='reload_module')
async def reload_module(ctx, module_name: str = None):
    """Reload a specific command module (Admin only)"""
    if not any(role.name.lower() in ["admin", "mod+"] for role in ctx.author.roles):
        await ctx.send("❌ This command requires administrator privileges.")
        return
    
    if not module_name:
        await ctx.send("❌ Please specify a module name (basic_commands, union_management, union_membership, union_info)")
        return
    
    module_path = f"cogs.{module_name}"
    
    try:
        await ctx.send(f"🔄 Reloading {module_path}...")
        
        # Unload and reload the module
        await bot.unload_extension(module_path)
        await bot.load_extension(module_path)
        
        # Sync commands after reload
        synced = await bot.tree.sync()
        
        await ctx.send(f"✅ Successfully reloaded {module_path} and synchronized {len(synced)} commands")
        logger.info(f"Module {module_path} reloaded by {ctx.author}")
        
    except Exception as e:
        await ctx.send(f"❌ Failed to reload {module_path}: {str(e)}")
        logger.error(f"Failed to reload {module_path}: {str(e)}")

@bot.command(name='bot_status')
async def bot_status(ctx):
    """Display bot status and command information"""
    tree_commands = len(bot.tree.get_commands())
    loaded_cogs = len(bot.cogs)
    guild_count = len(bot.guilds)
    
    status_embed = discord.Embed(
        title="🤖 Bot Status",
        color=0x00FF00,
        timestamp=discord.utils.utcnow()
    )
    
    status_embed.add_field(
        name="📊 Statistics",
        value=f"**Commands:** {tree_commands}\n**Modules:** {loaded_cogs}\n**Guilds:** {guild_count}",
        inline=True
    )
    
    status_embed.add_field(
        name="🔧 System",
        value=f"**Latency:** {round(bot.latency * 1000)}ms\n**Status:** Online",
        inline=True
    )
    
    # List loaded modules
    cog_names = list(bot.cogs.keys())
    if cog_names:
        status_embed.add_field(
            name="📦 Loaded Modules",
            value=", ".join(cog_names),
            inline=False
        )
    
    await ctx.send(embed=status_embed)

@bot.command(name='list_commands')
async def list_commands(ctx):
    """List all available slash commands"""
    commands = bot.tree.get_commands()
    
    if not commands:
        await ctx.send("❌ No commands are currently loaded.")
        return
    
    command_embed = discord.Embed(
        title="📋 Available Commands",
        description=f"Total: {len(commands)} commands",
        color=0x0099FF
    )
    
    # Group commands by category based on cog
    command_groups = {}
    for cmd in commands:
        cog_name = getattr(cmd, 'module', 'Unknown')
        if cog_name not in command_groups:
            command_groups[cog_name] = []
        command_groups[cog_name].append(f"`/{cmd.name}` - {cmd.description}")
    
    for group_name, group_commands in command_groups.items():
        if group_commands:
            # Truncate if too many commands
            display_commands = group_commands[:10]
            if len(group_commands) > 10:
                display_commands.append(f"... and {len(group_commands) - 10} more")
            
            command_embed.add_field(
                name=f"📁 {group_name}",
                value="\n".join(display_commands),
                inline=False
            )
    
    await ctx.send(embed=command_embed)

# Simple test command to verify slash command functionality
@bot.tree.command(name="ping", description="Test bot responsiveness")
async def ping_command(interaction: discord.Interaction):
    """Simple ping command to test functionality"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms", ephemeral=True)

# Graceful shutdown handling
async def shutdown_bot():
    """Gracefully shutdown the bot"""
    logger.info("Initiating bot shutdown...")
    await bot.close()
    logger.info("Bot shutdown completed")

# Main execution
def main():
    """Main function to run the bot"""
    if not TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        return
    
    try:
        logger.info("Starting Discord Union Bot...")
        bot.run(TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user interrupt")
    except discord.LoginFailure:
        logger.error("Invalid bot token provided")
    except Exception as e:
        logger.error(f"Fatal error occurred: {str(e)}")
        logger.debug(f"Error details: {traceback.format_exc()}")

if __name__ == "__main__":
    main()

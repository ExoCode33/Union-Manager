import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def username_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for username parameters"""
        if not current:
            # Show first 25 members if nothing is typed
            members = list(interaction.guild.members)[:25]
        else:
            # Filter members based on what's being typed
            current_lower = current.lower()
            members = [
                member for member in interaction.guild.members
                if (current_lower in member.name.lower() or 
                    current_lower in member.display_name.lower())
            ][:25]  # Limit to 25 results
        
        return [
            app_commands.Choice(name=f"{member.display_name} ({member.name})", value=member.name)
            for member in members
        ]
    
    def find_user_by_name(self, guild: discord.Guild, username: str) -> discord.Member:
        """Find a user in the guild by their username or display name"""
        username_lower = username.lower()
        
        # First try exact match on username
        for member in guild.members:
            if member.name.lower() == username_lower:
                return member
        
        # Then try exact match on display name
        for member in guild.members:
            if member.display_name.lower() == username_lower:
                return member
        
        # Finally try partial match on either name
        for member in guild.members:
            if (username_lower in member.name.lower() or 
                username_lower in member.display_name.lower()):
                return member
        
        return None

    def extract_user_id(self, discord_id: str) -> int:
        """Extract user ID from Discord mention or plain ID string"""
        # Remove <@ and > from mentions, handle both <@123> and <@!123> formats
        if discord_id.startswith('<@'):
            discord_id = discord_id.strip('<@!>')
        return int(discord_id)

    # /register_ign
    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(username="The Discord username of the user", ign="The IGN to register")
    @app_commands.autocomplete(username=username_autocomplete)
    async def register_ign(self, interaction: discord.Interaction, username: str, ign: str):
        # First try to find user by name
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
            # If not found by name, try to parse as ID/mention
            try:
                user_id = self.extract_user_id(username)
                try:
                    user = await interaction.guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message(f"❌ User not found: `{username}`")
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`")
                return
        
        user_display = f"{user.display_name} ({user.name})"
        
        conn = await get_connection()
        try:
            # Insert or update user with both IGN and username
            await conn.execute(
                "INSERT INTO users (username, user_id, ign) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET username = $1, ign = $3",
                user.name, user.id, ign
            )
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"✅ IGN for **{user_display}** set to `{ign}`")

    # /deregister_ign
    @app_commands.command(name="deregister_ign", description="Remove a user's IGN registration")
    @app_commands.describe(username="The Discord username of the user")
    @app_commands.autocomplete(username=username_autocomplete)
    async def deregister_ign(self, interaction: discord.Interaction, username: str):
        # First try to find user by name
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
            # If not found by name, try to parse as ID/mention
            try:
                user_id = self.extract_user_id(username)
                try:
                    user = await interaction.guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message(f"❌ User not found: `{username}`")
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`")
                return
        
        user_display = f"{user.display_name} ({user.name})"
        
        conn = await get_connection()
        try:
            # Check if user exists in database
            user_data = await conn.fetchrow("SELECT username, ign FROM users WHERE user_id = $1", user.id)
            if not user_data or not user_data['ign']:
                await interaction.response.send_message(f"⚠️ **{user_display}** has no IGN registered.")
                return
            
            # Remove IGN but keep other data
            await conn.execute("UPDATE users SET ign = NULL WHERE user_id = $1", user.id)
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"✅ IGN removed for **{user_display}**")

    # /search_user
    @app_commands.command(name="search_user", description="Search for a user by Discord username")
    @app_commands.describe(username="The Discord username of the user to search")
    @app_commands.autocomplete(username=username_autocomplete)
    async def search_user(self, interaction: discord.Interaction, username: str):
        # First try to find user by name
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
            # If not found by name, try to parse as ID/mention
            try:
                user_id = self.extract_user_id(username)
                try:
                    user = await interaction.guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message(f"❌ User not found: `{username}`")
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`")
                return
        
        user_display = f"{user.display_name} ({user.name})"
        
        conn = await get_connection()
        try:
            user_data = await conn.fetchrow("SELECT username, ign FROM users WHERE user_id = $1", user.id)
        finally:
            await conn.close()

        if user_data:
            # Update username if it's different (in case user changed their username)
            if user_data['username'] != user.name:
                conn = await get_connection()
                try:
                    await conn.execute("UPDATE users SET username = $1 WHERE user_id = $2", user.name, user.id)
                finally:
                    await conn.close()
            
            await interaction.response.send_message(f"**Discord:** {user_display}\n**IGN:** `{user_data['ign']}`")
        else:
            await interaction.response.send_message(f"⚠️ No IGN found for **{user_display}**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(BasicCommands(bot))
import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionMembership(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def username_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for username parameters"""
        if not current:
            members = list(interaction.guild.members)[:25]
        else:
            current_lower = current.lower()
            members = [
                member for member in interaction.guild.members
                if (current_lower in member.name.lower() or 
                    current_lower in member.display_name.lower())
            ][:25]
        
        return [
            app_commands.Choice(name=f"{member.display_name} ({member.name})", value=member.name)
            for member in members
        ]
    
    def find_user_by_name(self, guild: discord.Guild, username: str) -> discord.Member:
        """Find a user in the guild by their username or display name"""
        username_lower = username.lower()
        
        for member in guild.members:
            if member.name.lower() == username_lower:
                return member
        
        for member in guild.members:
            if member.display_name.lower() == username_lower:
                return member
        
        for member in guild.members:
            if (username_lower in member.name.lower() or 
                username_lower in member.display_name.lower()):
                return member
        
        return None

    def extract_user_id(self, discord_id: str) -> int:
        """Extract user ID from Discord mention or plain ID string"""
        if discord_id.startswith('<@'):
            discord_id = discord_id.strip('<@!>')
        return int(discord_id)

    def has_admin_or_mod_permissions(self, member: discord.Member) -> bool:
        """Check if user has Admin permissions"""
        if member.guild_permissions.administrator:
            return True
        
        admin_roles = {'admin'}
        for role in member.roles:
            if role.name.lower() in admin_roles:
                return True
        
        return False

    # /add_user_to_union
    @app_commands.command(name="add_user_to_union", description="Add a user to your union (leaders only)")
    @app_commands.describe(username="The Discord username of the user to add")
    @app_commands.autocomplete(username=username_autocomplete)
    async def add_user_to_union(self, interaction: discord.Interaction, username: str):
        # Find the user by username
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
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
        
        # Check if user is a union leader and get their union role
        conn = await get_connection()
        try:
            leader_id = int(interaction.user.id)
            leader_data = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1", leader_id)
            
            if not leader_data:
                await interaction.response.send_message(f"❌ You are not a union leader. Only union leaders can use this command.\nAdmins should use `/admin_add_user_to_union` instead.")
                return
            
            # Get the union role
            role_id = leader_data['role_id']
            role_obj = interaction.guild.get_role(role_id)
            
            if not role_obj:
                await interaction.response.send_message(f"❌ Your assigned union role no longer exists.")
                return
            
            # Insert or update user with union role and username
            user_id = int(user.id)
            await conn.execute(
                "INSERT INTO users (username, user_id, union_role_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET username = $1, union_role_id = $3",
                user.name, user_id, str(role_id)
            )
        finally:
            await conn.close()
        
        await user.add_roles(role_obj)
        await interaction.response.send_message(f"✅ {user.mention} added to your union `{role_obj.name}`.")

    # /remove_user_from_union
    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union (leaders only)")
    @app_commands.describe(username="The Discord username of the user to remove")
    @app_commands.autocomplete(username=username_autocomplete)
    async def remove_user_from_union(self, interaction: discord.Interaction, username: str):
        # Find the user by username
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
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
        
        # Check if user is a union leader and get their union role
        conn = await get_connection()
        try:
            leader_id = int(interaction.user.id)
            leader_data = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1", leader_id)
            
            if not leader_data:
                await interaction.response.send_message(f"❌ You are not a union leader. Only union leaders can use this command.\nAdmins should use `/admin_remove_user_from_union` instead.")
                return
            
            # Get the union role
            role_id = leader_data['role_id']
            role_obj = interaction.guild.get_role(role_id)
            
            if not role_obj:
                await interaction.response.send_message(f"❌ Your assigned union role no longer exists.")
                return
            
            # Remove user from union (set union_role_id to NULL)
            user_id = int(user.id)
            await conn.execute("UPDATE users SET union_role_id = NULL WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        await user.remove_roles(role_obj)
        await interaction.response.send_message(f"✅ {user.mention} removed from your union `{role_obj.name}`.")

    # /admin_add_user_to_union
    @app_commands.command(name="admin_add_user_to_union", description="Add a user to any union (Admin only)")
    @app_commands.describe(username="The Discord username of the user to add", role="Select the union role")
    @app_commands.autocomplete(username=username_autocomplete)
    async def admin_add_user_to_union(self, interaction: discord.Interaction, username: str, role: discord.Role):
        if not self.has_admin_or_mod_permissions(interaction.user):
            await interaction.response.send_message(f"❌ This command is only available to users with @Admin role.")
            return
        
        user = self.find_user_by_name(interaction.guild, username)
        if not user:
            try:
                user_id = self.extract_user_id(username)
                user = await interaction.guild.fetch_member(user_id)
            except:
                await interaction.response.send_message(f"❌ User not found: `{username}`")
                return
        
        conn = await get_connection()
        try:
            role_id = int(role.id)
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.")
                return
            
            user_id = int(user.id)
            await conn.execute(
                "INSERT INTO users (username, user_id, union_role_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET username = $1, union_role_id = $3",
                user.name, user_id, str(role_id)
            )
        finally:
            await conn.close()
        
        await user.add_roles(role)
        await interaction.response.send_message(f"✅ {user.mention} added to union `{role.name}` (Admin override).")

    # /admin_remove_user_from_union
    @app_commands.command(name="admin_remove_user_from_union", description="Remove a user from any union (Admin only)")
    @app_commands.describe(username="The Discord username of the user to remove", role="Select the union role")
    @app_commands.autocomplete(username=username_autocomplete)
    async def admin_remove_user_from_union(self, interaction: discord.Interaction, username: str, role: discord.Role):
        if not self.has_admin_or_mod_permissions(interaction.user):
            await interaction.response.send_message(f"❌ This command is only available to users with @Admin role.")
            return
        
        user = self.find_user_by_name(interaction.guild, username)
        if not user:
            try:
                user_id = self.extract_user_id(username)
                user = await interaction.guild.fetch_member(user_id)
            except:
                await interaction.response.send_message(f"❌ User not found: `{username}`")
                return
        
        conn = await get_connection()
        try:
            role_id = int(role.id)
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.")
                return
            
            user_id = int(user.id)
            await conn.execute("UPDATE users SET union_role_id = NULL WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        await user.remove_roles(role)
        await interaction.response.send_message(f"✅ {user.mention} removed from union `{role.name}` (Admin override).")


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionMembership(bot))
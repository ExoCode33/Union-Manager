import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
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
                    await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
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
        
        await interaction.response.send_message(f"✅ IGN for **{user_display}** set to `{ign}`", ephemeral=True)

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
                    await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
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
            
            await interaction.response.send_message(f"**Discord:** {user_display}\n**IGN:** `{user_data['ign']}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No IGN found for **{user_display}**.", ephemeral=True)

    # /register_role_as_union
    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union")
    @app_commands.describe(role="The Discord role to register as a union")
    async def register_union_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            # Ensure role.id is treated as an integer
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            await conn.execute(
                "INSERT INTO union_roles (role_id) VALUES ($1) ON CONFLICT (role_id) DO NOTHING",
                role_id
            )
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"✅ Registered union: `{role.name}`", ephemeral=True)

    # /deregister_role_as_union
    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role")
    @app_commands.describe(role="The union role to deregister")
    async def deregister_union_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", role_id)
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"🗑️ Deregistered union: `{role.name}`", ephemeral=True)

    # /appoint_union_leader
    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader")
    @app_commands.describe(user="The user to appoint", role="The union role to assign")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        conn = await get_connection()
        try:
            user_id = int(user.id) if isinstance(user.id, str) else user.id
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            await conn.execute(
                "INSERT INTO union_leaders (user_id, role_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET role_id = $2",
                user_id, role_id
            )
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"👑 `{user.display_name}` appointed as leader of `{role.name}`", ephemeral=True)

    # /dismiss_union_leader
    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader")
    @app_commands.describe(user="The leader to dismiss")
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            user_id = int(user.id) if isinstance(user.id, str) else user.id
            await conn.execute("DELETE FROM union_leaders WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"❌ `{user.display_name}` has been dismissed as a leader.", ephemeral=True)

    def has_admin_or_mod_permissions(self, member: discord.Member) -> bool:
        """Check if user has Admin or Mod permissions"""
        # Check for Administrator permission
        if member.guild_permissions.administrator:
            return True
        
        # Check for roles named "Admin", "Mod", "Moderator" (case insensitive)
        admin_mod_roles = {'admin', 'mod', 'moderator'}
        for role in member.roles:
            if role.name.lower() in admin_mod_roles:
                return True
        
        return False

    # /add_user_to_union
    @app_commands.command(name="add_user_to_union", description="Add a user to a union")
    @app_commands.describe(username="The Discord username of the user to add", role="The union role to add them to")
    @app_commands.autocomplete(username=username_autocomplete)
    async def add_user_to_union(self, interaction: discord.Interaction, username: str, role: discord.Role):
        # Find the user by username
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
            # If not found by name, try to parse as ID/mention
            try:
                user_id = self.extract_user_id(username)
                try:
                    user = await interaction.guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                return
        
        # Check permissions: Must be Admin/Mod OR union leader of the specified role
        has_override_permission = self.has_admin_or_mod_permissions(interaction.user)
        
        conn = await get_connection()
        try:
            # Check if the role is registered as a union
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.", ephemeral=True)
                return
            
            # If not Admin/Mod, check if they're a union leader for this specific role
            if not has_override_permission:
                leader_id = int(interaction.user.id) if isinstance(interaction.user.id, str) else interaction.user.id
                leader = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1 AND role_id = $2", leader_id, role_id)
                if not leader:
                    await interaction.response.send_message(f"❌ You are not a leader of `{role.name}` union and don't have override permissions.", ephemeral=True)
                    return
            
            # Insert or update user with union role and username
            user_id = int(user.id) if isinstance(user.id, str) else user.id
            await conn.execute(
                "INSERT INTO users (username, user_id, union_role_id) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET username = $1, union_role_id = $3",
                user.name, user_id, str(role_id)
            )
        finally:
            await conn.close()
        
        await user.add_roles(role)
        permission_note = " (Admin/Mod override)" if has_override_permission else ""
        await interaction.response.send_message(f"✅ {user.mention} added to union `{role.name}`{permission_note}.", ephemeral=True)

    # /remove_user_from_union
    @app_commands.command(name="remove_user_from_union", description="Remove a user from a union")
    @app_commands.describe(username="The Discord username of the user to remove", role="The union role to remove them from")
    @app_commands.autocomplete(username=username_autocomplete)
    async def remove_user_from_union(self, interaction: discord.Interaction, username: str, role: discord.Role):
        # Find the user by username
        user = self.find_user_by_name(interaction.guild, username)
        
        if not user:
            # If not found by name, try to parse as ID/mention
            try:
                user_id = self.extract_user_id(username)
                try:
                    user = await interaction.guild.fetch_member(user_id)
                except:
                    await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message(f"❌ User not found: `{username}`", ephemeral=True)
                return
        
        # Check permissions: Must be Admin/Mod OR union leader of the specified role
        has_override_permission = self.has_admin_or_mod_permissions(interaction.user)
        
        conn = await get_connection()
        try:
            # Check if the role is registered as a union
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.", ephemeral=True)
                return
            
            # If not Admin/Mod, check if they're a union leader for this specific role
            if not has_override_permission:
                leader_id = int(interaction.user.id) if isinstance(interaction.user.id, str) else interaction.user.id
                leader = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1 AND role_id = $2", leader_id, role_id)
                if not leader:
                    await interaction.response.send_message(f"❌ You are not a leader of `{role.name}` union and don't have override permissions.", ephemeral=True)
                    return
            
            # Remove user from union (set union_role_id to NULL)
            user_id = int(user.id) if isinstance(user.id, str) else user.id
            await conn.execute("UPDATE users SET union_role_id = NULL WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        await user.remove_roles(role)
        permission_note = " (Admin/Mod override)" if has_override_permission else ""
        await interaction.response.send_message(f"✅ {user.mention} removed from union `{role.name}`{permission_note}.", ephemeral=True)

    # /show_union_detail
    @app_commands.command(name="show_union_detail", description="Show all registered union roles with member lists")
    async def show_union_detail(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_id FROM union_roles")
            # Get all users with their union roles, usernames, and IGNs
            members = await conn.fetch("SELECT union_role_id, username, ign FROM users WHERE union_role_id IS NOT NULL ORDER BY username")
        finally:
            await conn.close()

        if not unions:
            await interaction.response.send_message("📭 No unions found.", ephemeral=True)
            return

        # Group members by union role
        union_members = {}
        for member in members:
            role_id = member['union_role_id']
            if role_id not in union_members:
                union_members[role_id] = []
            union_members[role_id].append(member)

        lines = []
        for row in unions:
            rid = row['role_id']  # This is already an integer from DB
            role = guild.get_role(rid)  # Use directly, no int() conversion needed
            if role:
                role_members = union_members.get(str(rid), [])
                member_count = len(role_members)
                
                lines.append(f"**{role.name}** — {member_count}/30 members")
                
                if role_members:
                    for member in role_members:
                        username = member['username']
                        ign = member['ign'] or "No IGN"
                        lines.append(f"  • **{username}** | IGN: `{ign}`")
                else:
                    lines.append("  • No members")
                
                lines.append("")  # Add empty line between unions

        # Remove the last empty line
        if lines and lines[-1] == "":
            lines.pop()

        # Split into chunks if message is too long (Discord has 2000 character limit)
        message = "\n".join(lines)
        if len(message) <= 2000:
            await interaction.response.send_message(message, ephemeral=True)
        else:
            # Split into multiple messages
            chunks = []
            current_chunk = ""
            
            for line in lines:
                if len(current_chunk + line + "\n") <= 2000:
                    current_chunk += line + "\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.rstrip())
                    current_chunk = line + "\n"
            
            if current_chunk:
                chunks.append(current_chunk.rstrip())
            
            # Send first chunk as response
            await interaction.response.send_message(chunks[0], ephemeral=True)
            
            # Send remaining chunks as follow-ups
            for chunk in chunks[1:]:
                await interaction.followup.send(chunk, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

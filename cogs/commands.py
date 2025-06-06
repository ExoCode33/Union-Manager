import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def union_role_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        """Autocomplete for union role parameters - only shows registered union roles"""
        conn = await get_connection()
        try:
            # Get all registered union roles
            union_roles = await conn.fetch("SELECT role_id FROM union_roles")
        finally:
            await conn.close()
        
        guild = interaction.guild
        choices = []
        
        for union_role in union_roles:
            role = guild.get_role(union_role['role_id'])
            if role:
                # Filter based on what's being typed
                if not current or current.lower() in role.name.lower():
                    choices.append(app_commands.Choice(name=role.name, value=str(role.id)))
        
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
        
        # Refresh the cache after adding a new union role
        await self.refresh_union_roles_cache()
        
        await interaction.response.send_message(f"✅ Registered union: `{role.name}`")

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
        
        # Refresh the cache after removing a union role
        await self.refresh_union_roles_cache()
        
        await interaction.response.send_message(f"🗑️ Deregistered union: `{role.name}`")

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
        
        await interaction.response.send_message(f"👑 `{user.display_name}` appointed as leader of `{role.name}`")

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
        
        await interaction.response.send_message(f"❌ `{user.display_name}` has been dismissed as a leader.")

    def has_admin_or_mod_permissions(self, member: discord.Member) -> bool:
        """Check if user has Admin permissions"""
        # Check for Administrator permission
        if member.guild_permissions.administrator:
            return True
        
        # Check for roles named "Admin" (case insensitive)
        admin_roles = {'admin'}
        for role in member.roles:
            if role.name.lower() in admin_roles:
                return True
        
        return False

    # /add_user_to_union
    @app_commands.command(name="add_user_to_union", description="Add a user to a union")
    @app_commands.describe(username="The Discord username of the user to add", role="Type the exact union role name")
    @app_commands.autocomplete(username=username_autocomplete)
    async def add_user_to_union(self, interaction: discord.Interaction, username: str, role: str):
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
        
        # Check permissions: Must be Admin OR union leader of the specified role
        has_admin_permission = self.has_admin_or_mod_permissions(interaction.user)
        
        conn = await get_connection()
        try:
            # Check if the role is registered as a union
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.")
                return
            
            # Check if they're a union leader for this specific role
            leader_id = int(interaction.user.id) if isinstance(interaction.user.id, str) else interaction.user.id
            is_union_leader = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1 AND role_id = $2", leader_id, role_id)
            
            # If not Admin and not union leader, deny access
            if not has_admin_permission and not is_union_leader:
                await interaction.response.send_message(f"❌ You are not a leader of `{role.name}` union and don't have override permissions.")
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
        
        # Show admin override only if admin is not the union leader
        permission_note = " (Admin override)" if has_admin_permission and not is_union_leader else ""
        await interaction.response.send_message(f"✅ {user.mention} added to union `{role.name}`{permission_note}.")

    # /remove_user_from_union
    @app_commands.command(name="remove_user_from_union", description="Remove a user from a union")
    @app_commands.describe(username="The Discord username of the user to remove", role="Type the exact union role name")
    @app_commands.autocomplete(username=username_autocomplete)
    async def remove_user_from_union(self, interaction: discord.Interaction, username: str, role: str):
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
        
        # Check permissions: Must be Admin OR union leader of the specified role
        has_admin_permission = self.has_admin_or_mod_permissions(interaction.user)
        
        conn = await get_connection()
        try:
            # Check if the role is registered as a union
            role_id = int(role.id) if isinstance(role.id, str) else role.id
            union_role = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role_id)
            if not union_role:
                await interaction.response.send_message(f"❌ `{role.name}` is not a registered union role.")
                return
            
            # Check if they're a union leader for this specific role
            leader_id = int(interaction.user.id) if isinstance(interaction.user.id, str) else interaction.user.id
            is_union_leader = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1 AND role_id = $2", leader_id, role_id)
            
            # If not Admin and not union leader, deny access
            if not has_admin_permission and not is_union_leader:
                await interaction.response.send_message(f"❌ You are not a leader of `{role.name}` union and don't have override permissions.")
                return
            
            # Remove user from union (set union_role_id to NULL)
            user_id = int(user.id) if isinstance(user.id, str) else user.id
            await conn.execute("UPDATE users SET union_role_id = NULL WHERE user_id = $1", user_id)
        finally:
            await conn.close()
        
        await user.remove_roles(role)
        
        # Show admin override only if admin is not the union leader
        permission_note = " (Admin override)" if has_admin_permission and not is_union_leader else ""
        await interaction.response.send_message(f"✅ {user.mention} removed from union `{role.name}`{permission_note}.")

    # /show_union_leader
    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assigned unions")
    async def show_union_leader(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            # Get all union leaders with their role assignments
            leaders = await conn.fetch("SELECT user_id, role_id FROM union_leaders ORDER BY role_id")
        finally:
            await conn.close()

        if not leaders:
            await interaction.response.send_message("👑 No union leaders found.")
            return

        lines = ["👑 **Union Leaders:**", ""]
        
        for leader in leaders:
            user_id = leader['user_id']
            role_id = leader['role_id']
            
            # Get the Discord member
            discord_member = guild.get_member(user_id)
            if discord_member:
                display_name = discord_member.display_name
                username = discord_member.name
                user_display = f"{display_name} ({username})"
            else:
                # Fallback if member not found in guild
                user_display = f"Unknown User (ID: {user_id})"
            
            # Get the union role
            role = guild.get_role(role_id)
            if role:
                role_name = role.name
            else:
                role_name = f"Unknown Role (ID: {role_id})"
            
            lines.append(f"• **{user_display}** → `{role_name}`")

        message = "\n".join(lines)
        await interaction.response.send_message(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

    # /show_union_detail
    @app_commands.command(name="show_union_detail", description="Show all union roles with member lists")
    async def show_union_detail(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_id FROM union_roles")
            members = await conn.fetch("SELECT union_role_id, username, user_id, ign FROM users WHERE union_role_id IS NOT NULL ORDER BY username")
            leaders = await conn.fetch("SELECT user_id, role_id FROM union_leaders")
        finally:
            await conn.close()

        if not unions:
            await interaction.response.send_message("📭 No unions found.")
            return

        leader_map = {}
        for leader in leaders:
            role_id = str(leader['role_id'])
            if role_id not in leader_map:
                leader_map[role_id] = set()
            leader_map[role_id].add(leader['user_id'])

        union_members = {}
        for member in members:
            role_id = member['union_role_id']
            if role_id not in union_members:
                union_members[role_id] = []
            union_members[role_id].append(member)

        lines = []
        for row in unions:
            rid = row['role_id']
            role = guild.get_role(rid)
            if role:
                role_members = union_members.get(str(rid), [])
                member_count = len(role_members)
                
                lines.append(f"**{role.name}** — {member_count}/30 members")
                
                if role_members:
                    for member in role_members:
                        discord_member = guild.get_member(member['user_id'])
                        if discord_member:
                            display_name = discord_member.display_name
                        else:
                            display_name = member['username']
                        
                        is_leader = str(rid) in leader_map and member['user_id'] in leader_map[str(rid)]
                        crown_emoji = " 👑" if is_leader else ""
                        ign = member['ign'] or "No IGN"
                        lines.append(f"  • **{display_name}**{crown_emoji} | IGN: `{ign}`")
                else:
                    lines.append("  • No members")
                
                lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        message = "\n".join(lines)
        await interaction.response.send_message(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

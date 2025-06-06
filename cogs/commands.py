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
            await conn.execute(
                "INSERT INTO users (discord_id, ign) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET ign = $2",
                user.id, ign
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
            user_data = await conn.fetchrow("SELECT ign FROM users WHERE discord_id = $1", user.id)
        finally:
            await conn.close()

        if user_data:
            await interaction.response.send_message(f"**Discord:** {user_display}\n**IGN:** `{user_data['ign']}`", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No IGN found for **{user_display}**.", ephemeral=True)

    # /register_role_as_union
    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union")
    @app_commands.describe(role="The Discord role to register as a union")
    async def register_union_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO unions (role_id, name) VALUES ($1, $2) ON CONFLICT (role_id) DO NOTHING",
                str(role.id), role.name
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
            await conn.execute("DELETE FROM unions WHERE role_id = $1", str(role.id))
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"🗑️ Deregistered union: `{role.name}`", ephemeral=True)

    # /appoint_union_leader
    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader")
    @app_commands.describe(user="The user to appoint", role="The union role to assign")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO leaders (user_id, role_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET role_id = $2",
                str(user.id), str(role.id)
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
            await conn.execute("DELETE FROM leaders WHERE user_id = $1", str(user.id))
        finally:
            await conn.close()
        
        await interaction.response.send_message(f"❌ `{user.display_name}` has been dismissed as a leader.", ephemeral=True)

    # /add_user_to_union
    @app_commands.command(name="add_user_to_union", description="Add a user to your union")
    @app_commands.describe(user="User to add to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_id = str(interaction.user.id)
        conn = await get_connection()
        try:
            leader = await conn.fetchrow("SELECT role_id FROM leaders WHERE user_id = $1", leader_id)
            if not leader:
                await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
                return
            await conn.execute("UPDATE users SET role_id = $1 WHERE discord_id = $2", leader['role_id'], str(user.id))
        finally:
            await conn.close()
        
        await user.add_roles(discord.Object(id=int(leader['role_id'])))
        await interaction.response.send_message(f"✅ {user.mention} added to your union.", ephemeral=True)

    # /remove_user_from_union
    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union")
    @app_commands.describe(user="User to remove from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_id = str(interaction.user.id)
        conn = await get_connection()
        try:
            leader = await conn.fetchrow("SELECT role_id FROM leaders WHERE user_id = $1", leader_id)
            if not leader:
                await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
                return
            await conn.execute("UPDATE users SET role_id = NULL WHERE discord_id = $1", str(user.id))
        finally:
            await conn.close()
        
        await user.remove_roles(discord.Object(id=int(leader['role_id'])))
        await interaction.response.send_message(f"✅ {user.mention} removed from your union.", ephemeral=True)

    # /show_union_detail
    @app_commands.command(name="show_union_detail", description="Show all registered union roles and member counts")
    async def show_union_detail(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_id, name FROM unions")
            members = await conn.fetch("SELECT role_id, COUNT(*) FROM users WHERE role_id IS NOT NULL GROUP BY role_id")
        finally:
            await conn.close()

        count_map = {row['role_id']: row['count'] for row in members}
        if not unions:
            await interaction.response.send_message("📭 No unions found.", ephemeral=True)
            return

        lines = []
        for row in unions:
            rid = row['role_id']
            role = guild.get_role(int(rid))
            if role:
                lines.append(f"{role.mention} — {count_map.get(rid, 0)}/30 members")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

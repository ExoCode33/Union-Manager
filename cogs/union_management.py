import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionManagement(bot))

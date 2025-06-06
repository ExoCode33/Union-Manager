import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_union(self, user_id):
        conn = await get_connection()
        try:
            result = await conn.fetchrow("SELECT union_name FROM users WHERE discord_id = $1", str(user_id))
            return result['union_name'] if result else None
        finally:
            await conn.close()

    @app_commands.command(name="add_user_to_union", description="Add a user to your union.")
    async def add_user_to_union(self, interaction: discord.Interaction, user: discord.Member):
        user_union = await self.get_user_union(interaction.user.id)
        if not user_union:
            await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "UPDATE users SET union_name = $1 WHERE discord_id = $2",
                user_union, str(user.id)
            )
            await interaction.response.send_message(f"✅ {user.mention} has been added to your union.")
        finally:
            await conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union.")
    async def remove_user_from_union(self, interaction: discord.Interaction, user: discord.Member):
        user_union = await self.get_user_union(interaction.user.id)
        target_union = await self.get_user_union(user.id)

        if not user_union or user_union != target_union:
            await interaction.response.send_message("❌ You can only remove users from your own union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "UPDATE users SET union_name = NULL WHERE discord_id = $1",
                str(user.id)
            )
            await interaction.response.send_message(f"✅ {user.mention} has been removed from your union.")
        finally:
            await conn.close()

    @app_commands.command(name="register_role_as_union", description="Register a role as a union role.")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO union_roles (role_id) VALUES ($1) ON CONFLICT DO NOTHING",
                str(role.id)
            )
            await interaction.response.send_message(f"✅ {role.name} has been registered as a union role.")
        finally:
            await conn.close()

    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role.")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", str(role.id))
            await interaction.response.send_message(f"✅ {role.name} has been deregistered as a union role.")
        finally:
            await conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader.")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, union_name: str):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO union_leaders (discord_id, union_name) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET union_name = $2",
                str(user.id), union_name
            )
            await conn.execute(
                "INSERT INTO users (discord_id, union_name) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET union_name = $2",
                str(user.id), union_name
            )
            await interaction.response.send_message(f"✅ {user.mention} has been appointed as the leader of `{union_name}`.")
        finally:
            await conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader.")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_leaders WHERE discord_id = $1", str(user.id))
            await interaction.response.send_message(f"✅ {user.mention} is no longer a union leader.")
        finally:
            await conn.close()

    @app_commands.command(name="register_ign", description="Register your in-game name.")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        user_union = await self.get_user_union(interaction.user.id)
        if not user_union:
            await interaction.response.send_message("❌ You must be a union leader to register an IGN.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO users (discord_id, ign, union_name) VALUES ($1, $2, $3) ON CONFLICT (discord_id) DO UPDATE SET ign = $2",
                str(interaction.user.id), ign, user_union
            )
            await interaction.response.send_message(f"✅ {interaction.user.mention}'s IGN has been registered as `{ign}`.")
        finally:
            await conn.close()

    @app_commands.command(name="search_user", description="Search for a user by IGN or Discord name.")
    async def search_user(self, interaction: discord.Interaction, query: str):
        conn = await get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT ign, union_name FROM users WHERE ign ILIKE $1 OR discord_id = $2",
                f"%{query}%", str(interaction.user.id)
            )
            if result:
                await interaction.response.send_message(
                    f"**Discord:** {interaction.user.mention}
**IGN:** {result['ign']}
**Union:** {result['union_name']}"
                )
            else:
                await interaction.response.send_message("❌ No user found.")
        finally:
            await conn.close()

    @app_commands.command(name="show_union_detail", description="List all union roles registered.")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("SELECT role_id FROM union_roles")
            if not rows:
                await interaction.response.send_message("❌ No union roles registered.")
                return

            role_mentions = []
            for row in rows:
                role = interaction.guild.get_role(int(row["role_id"]))
                if role:
                    role_mentions.append(role.mention)

            await interaction.response.send_message("📋 **Registered Union Roles:**
" + "
".join(role_mentions))
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionCommands(bot))

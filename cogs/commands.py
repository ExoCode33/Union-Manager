
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
            return result["union_name"] if result else None
        finally:
            await conn.close()

    @app_commands.command(name="add_user_to_union", description="Add a user to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, user: discord.Member):
        union = await self.get_user_union(interaction.user.id)
        if not union:
            await interaction.response.send_message("❌ You are not part of a union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO users (discord_id, union_name) VALUES ($1, $2) "
                "ON CONFLICT (discord_id) DO UPDATE SET union_name = EXCLUDED.union_name",
                str(user.id), union
            )
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {user.mention} has been added to union `{union}`.")

    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, user: discord.Member):
        union = await self.get_user_union(interaction.user.id)
        if not union:
            await interaction.response.send_message("❌ You are not part of a union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            result = await conn.execute(
                "UPDATE users SET union_name = NULL WHERE discord_id = $1 AND union_name = $2",
                str(user.id), union
            )
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {user.mention} has been removed from your union.")

    @app_commands.command(name="register_role_as_union", description="Register a role as a union")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO unions (role_id) VALUES ($1) ON CONFLICT DO NOTHING", str(role.id))
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {role.mention} has been registered as a union.")

    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM unions WHERE role_id = $1", str(role.id))
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {role.mention} has been deregistered.")

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO union_leaders (discord_id) VALUES ($1) ON CONFLICT DO NOTHING",
                str(user.id)
            )
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {user.mention} is now a union leader.")

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader")
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_leaders WHERE discord_id = $1", str(user.id))
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ {user.mention} is no longer a union leader.")

    @app_commands.command(name="register_ign", description="Register your in-game name")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO users (discord_id, ign) VALUES ($1, $2) "
                "ON CONFLICT (discord_id) DO UPDATE SET ign = EXCLUDED.ign",
                str(interaction.user.id), ign
            )
        finally:
            await conn.close()
        await interaction.response.send_message(f"✅ IGN `{ign}` registered.")

    @app_commands.command(name="search_user", description="Search a user by IGN or Discord name")
    async def search_user(self, interaction: discord.Interaction, query: str):
        conn = await get_connection()
        try:
            result = await conn.fetchrow(
                "SELECT ign, union_name FROM users WHERE ign ILIKE $1 OR discord_id = $2",
                f"%{query}%", str(interaction.user.id)
            )
        finally:
            await conn.close()

        if result:
            await interaction.response.send_message(
                f"📌 **User Info**\n"
                f"**Discord:** {interaction.user.mention}\n"
                f"**IGN:** {result['ign']}\n"
                f"**Union:** {result['union_name'] or 'None'}"
            )
        else:
            await interaction.response.send_message("❌ User not found.")

    @app_commands.command(name="show_union_detail", description="List all registered union roles")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("SELECT role_id FROM unions")
        finally:
            await conn.close()

        if rows:
            mentions = [f"<@&{row['role_id']}>" for row in rows]
            await interaction.response.send_message("📋 **Registered Unions:**\n" + "\n".join(mentions))
        else:
            await interaction.response.send_message("❌ No unions registered.")

async def setup(bot):
    await bot.add_cog(UnionCommands(bot))

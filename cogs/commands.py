import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_union(self, user_id):
        conn = await get_connection()
        async with conn.transaction():
            user = await conn.fetchrow("SELECT * FROM union_members WHERE discord_id = $1", str(user_id))
        await conn.close()
        return user

    @app_commands.command(name="register_ign", description="Register your in-game name (IGN)")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO union_members (discord_id, ign) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET ign = $2",
                str(interaction.user.id), ign
            )
        await conn.close()
        await interaction.response.send_message(f"✅ {interaction.user.mention}'s IGN has been registered as `{ign}`.")

    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO unions (role_id, name) VALUES ($1, $2) ON CONFLICT (role_id) DO NOTHING",
                str(role.id), role.name
            )
        await conn.close()
        await interaction.response.send_message(f"✅ `{role.name}` has been registered as a union.")

    @app_commands.command(name="deregister_role_as_union", description="Remove a union registration from a role")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute("DELETE FROM unions WHERE role_id = $1", str(role.id))
        await conn.close()
        await interaction.response.send_message(f"❌ `{role.name}` is no longer registered as a union.")

    @app_commands.command(name="appoint_union_leader", description="Appoint a member as the union leader")
    async def appoint_union_leader(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "UPDATE union_members SET is_leader = TRUE WHERE discord_id = $1",
                str(member.id)
            )
        await conn.close()
        await interaction.response.send_message(f"👑 `{member.display_name}` has been appointed as a union leader.")

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a member from union leadership")
    async def dismiss_union_leader(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "UPDATE union_members SET is_leader = FALSE WHERE discord_id = $1",
                str(member.id)
            )
        await conn.close()
        await interaction.response.send_message(f"⚠️ `{member.display_name}` has been dismissed from union leadership.")

    @app_commands.command(name="add_user_to_union", description="Assign a user to a union")
    async def add_user_to_union(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "UPDATE union_members SET union_name = $1 WHERE discord_id = $2",
                role.name, str(member.id)
            )
        await conn.close()
        await interaction.response.send_message(f"📦 `{member.display_name}` has been added to the union `{role.name}`.")

    @app_commands.command(name="remove_user_from_union", description="Remove a user from their union")
    async def remove_user_from_union(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        async with conn.transaction():
            await conn.execute(
                "UPDATE union_members SET union_name = NULL WHERE discord_id = $1",
                str(member.id)
            )
        await conn.close()
        await interaction.response.send_message(f"📤 `{member.display_name}` has been removed from their union.")

    @app_commands.command(name="search_user", description="Search a user's union membership")
    async def search_user(self, interaction: discord.Interaction, user: discord.User):
        user_union = await self.get_user_union(user.id)
        if not user_union:
            await interaction.response.send_message("❌ No data found for this user.")
            return

        message = (
            f"**Discord:** {interaction.user.mention}
"
            f"**IGN:** `{user_union['ign']}`
"
            f"**Union:** `{user_union['union_name']}`
"
            f"**Leader:** {'✅' if user_union['is_leader'] else '❌'}"
        )
        await interaction.response.send_message(message)

    @app_commands.command(name="show_union_detail", description="Show details for all registered unions")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        async with conn.transaction():
            rows = await conn.fetch("SELECT * FROM unions")
        await conn.close()

        if not rows:
            await interaction.response.send_message("ℹ️ No unions registered.")
            return

        message = "📋 **Registered Unions:**
" + "
".join(
            f"- {r['name']} (Role ID: {r['role_id']})" for r in rows
        )
        await interaction.response.send_message(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(UnionManager(bot))

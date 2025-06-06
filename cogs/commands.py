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
            row = await conn.fetchrow("SELECT union_name FROM users WHERE user_id = $1", user_id)
            return row["union_name"] if row else None
        finally:
            await conn.close()

    @app_commands.command(name="register_role_as_union", description="Register a role as a union.")
    @app_commands.checks.has_permissions(administrator=True)
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO unions (role_id) VALUES ($1) ON CONFLICT DO NOTHING", role.id)
            await interaction.response.send_message(f"✅ Role {role.name} registered as a union.", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_role_as_union", description="Deregister a role as a union.")
    @app_commands.checks.has_permissions(administrator=True)
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM unions WHERE role_id = $1", role.id)
            await interaction.response.send_message(f"✅ Role {role.name} deregistered as a union.", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO union_leaders (user_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING", user.id, role.id)
            await interaction.response.send_message(f"✅ {user.mention} has been appointed as a leader of {role.name}.", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader.")
    @app_commands.checks.has_permissions(manage_roles=True)
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_leaders WHERE user_id = $1", user.id)
            await interaction.response.send_message(f"✅ {user.mention} has been dismissed from leadership.", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="register_ign", description="Register your in-game name.")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        user = interaction.user
        user_union = await self.get_user_union(user.id)
        if not user_union:
            await interaction.response.send_message("❌ You are not in any union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO users (user_id, ign, union_name) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET ign = $2, union_name = $3", user.id, ign, user_union)
            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
        finally:
            await conn.close()

    @app_commands.command(name="add_to_union", description="Add a user to your union.")
    async def add_to_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_union = await self.get_user_union(interaction.user.id)
        if not leader_union:
            await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO users (user_id, union_name) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET union_name = $2", user.id, leader_union)
            await interaction.response.send_message(f"✅ {user.mention} added to the union `{leader_union}`.")
        finally:
            await conn.close()

    @app_commands.command(name="remove_from_union", description="Remove a user from your union.")
    async def remove_from_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_union = await self.get_user_union(interaction.user.id)
        user_union = await self.get_user_union(user.id)
        if leader_union != user_union:
            await interaction.response.send_message("❌ You can only remove users from your own union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("UPDATE users SET union_name = NULL WHERE user_id = $1", user.id)
            await interaction.response.send_message(f"✅ {user.mention} removed from the union `{leader_union}`.")
        finally:
            await conn.close()

    @app_commands.command(name="list_union_detail", description="List all registered union roles.")
    async def list_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            records = await conn.fetch("SELECT role_id FROM unions")
            roles = [interaction.guild.get_role(r["role_id"]).mention for r in records if interaction.guild.get_role(r["role_id"])]
            await interaction.response.send_message("Registered union roles:
" + "
".join(roles))
        finally:
            await conn.close()

    @app_commands.command(name="list_union_leaders", description="List all union leaders.")
    async def list_union_leaders(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            records = await conn.fetch("SELECT user_id, role_id FROM union_leaders")
            leaders = [f"<@{r['user_id']}> - {interaction.guild.get_role(r['role_id']).mention}" for r in records if interaction.guild.get_role(r['role_id'])]
            await interaction.response.send_message("Union Leaders:
" + "
".join(leaders))
        finally:
            await conn.close()

    @app_commands.command(name="search_user", description="Search for a user by Discord name or IGN.")
    async def search_user(self, interaction: discord.Interaction, keyword: str):
        conn = await get_connection()
        try:
            records = await conn.fetch("SELECT user_id, ign, union_name FROM users WHERE ign ILIKE $1", f"%{keyword}%")
            if not records:
                await interaction.response.send_message("❌ No user found with that IGN.", ephemeral=True)
                return
            response = "
".join([f"<@{r['user_id']}> - IGN: `{r['ign']}` - Union: `{r['union_name']}`" for r in records])
            await interaction.response.send_message(response)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionCommands(bot))

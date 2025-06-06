import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_union(self, user_id):
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT union_role_id FROM users WHERE user_id = $1", str(user_id))
            return row["union_role_id"] if row else None
        finally:
            await conn.close()

    async def is_union_leader(self, user_id):
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT is_leader FROM users WHERE user_id = $1", str(user_id))
            return row["is_leader"] if row else False
        finally:
            await conn.close()

    @app_commands.command(name="register_ign", description="Register your in-game name")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        user = interaction.user
        user_union = await self.get_user_union(user.id)

        if not user_union:
            await interaction.response.send_message("❌ You must be part of a union before registering your IGN.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("""
                INSERT INTO users (user_id, ign, union_role_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET ign = $2
            """, str(user.id), ign, user_union)

            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
        finally:
            await conn.close()

    @app_commands.command(name="set_union", description="Assign a user to a union")
    async def set_union(self, interaction: discord.Interaction, member: discord.Member, union: discord.Role):
        caller_id = interaction.user.id
        caller_union = await self.get_user_union(caller_id)
        is_leader = await self.is_union_leader(caller_id)

        if not is_leader or caller_union != union.id:
            await interaction.response.send_message("❌ You must be a leader of this union to assign users.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("""
                INSERT INTO users (user_id, union_role_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE SET union_role_id = $2
            """, str(member.id), union.id)

            await member.add_roles(union)
            await interaction.response.send_message(f"✅ {member.mention} has been added to {union.name}.")
        finally:
            await conn.close()

    @app_commands.command(name="unset_union", description="Remove a user from their union")
    async def unset_union(self, interaction: discord.Interaction, member: discord.Member):
        caller_id = interaction.user.id
        caller_union = await self.get_user_union(caller_id)
        is_leader = await self.is_union_leader(caller_id)

        target_union = await self.get_user_union(member.id)

        if not is_leader or caller_union != target_union:
            await interaction.response.send_message("❌ You can only remove users from your own union.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("UPDATE users SET union_role_id = NULL WHERE user_id = $1", str(member.id))
            if union := discord.utils.get(member.roles, id=target_union):
                await member.remove_roles(union)
            await interaction.response.send_message(f"✅ {member.mention} has been removed from their union.")
        finally:
            await conn.close()

    @app_commands.command(name="register_union_role", description="Register a Discord role as a union")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def register_union_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("INSERT INTO union_roles (role_id) VALUES ($1) ON CONFLICT DO NOTHING", role.id)
            await interaction.response.send_message(f"✅ Registered {role.name} as a union role.")
        finally:
            await conn.close()

    @app_commands.command(name="deregister_union_role", description="Remove a union role")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def deregister_union_role(self, interaction: discord.Interaction, role: discord.Role):
        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", role.id)
            await interaction.response.send_message(f"✅ Deregistered {role.name} as a union role.")
        finally:
            await conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a user as union leader")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def appoint_union_leader(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute("UPDATE users SET is_leader = TRUE WHERE user_id = $1", str(member.id))
            await interaction.response.send_message(f"✅ {member.mention} is now a union leader.")
        finally:
            await conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader")
    @app_commands.checks.has_any_role("Admin", "Mod")
    async def dismiss_union_leader(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        try:
            await conn.execute("UPDATE users SET is_leader = FALSE WHERE user_id = $1", str(member.id))
            await interaction.response.send_message(f"✅ {member.mention} is no longer a union leader.")
        finally:
            await conn.close()

    @app_commands.command(name="show_user", description="Show user IGN and union")
    async def show_user(self, interaction: discord.Interaction, member: discord.Member):
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT ign, union_role_id FROM users WHERE user_id = $1", str(member.id))
            if row:
                union_name = discord.utils.get(interaction.guild.roles, id=row["union_role_id"]).name
                await interaction.response.send_message(f"👤 {member.mention}\nIGN: `{row['ign']}`\nUnion: {union_name}")
            else:
                await interaction.response.send_message(f"❌ No record found for {member.mention}.")
        finally:
            await conn.close()

    @app_commands.command(name="list_union_roles", description="List all registered union roles")
    async def list_union_roles(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("SELECT role_id FROM union_roles")
            if not rows:
                await interaction.response.send_message("❌ No union roles registered.")
                return
            role_names = [discord.utils.get(interaction.guild.roles, id=row["role_id"]).mention for row in rows]
            await interaction.response.send_message("🔗 Registered Union Roles:\n" + "\n".join(role_names))
        finally:
            await conn.close()

    @app_commands.command(name="search_user", description="Search for a user by IGN or Discord name")
    async def search_user(self, interaction: discord.Interaction, query: str):
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT user_id, ign, union_role_id FROM users WHERE ign ILIKE $1", f"%{query}%")
            if row:
                member = interaction.guild.get_member(int(row["user_id"]))
                union = discord.utils.get(interaction.guild.roles, id=row["union_role_id"])
                await interaction.response.send_message(f"👤 {member.mention if member else row['user_id']}\nIGN: `{row['ign']}`\nUnion: {union.name if union else 'Unknown'}")
            else:
                await interaction.response.send_message("❌ No matching user found.")
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionCommands(bot))

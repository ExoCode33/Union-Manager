import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_admin_or_mod(interaction: discord.Interaction):
        roles = [role.name.lower() for role in interaction.user.roles]
        return 'admin' in roles or 'mod' in roles

    def is_union_leader(interaction: discord.Interaction):
        roles = [role.name.lower() for role in interaction.user.roles]
        return 'union leader' in roles

    async def get_user_union(self, user_id):
        async with (await get_connection()) as conn:
            row = await conn.fetchrow("SELECT union_name FROM users WHERE discord_id = $1", str(user_id))
            return row["union_name"] if row else None

    @app_commands.command(name="register_ign", description="Register your in-game name (IGN).")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        user = interaction.user
        user_union = await self.get_user_union(user.id)
        if not user_union:
            await interaction.response.send_message("❌ You must belong to a union to register an IGN.", ephemeral=True)
            return
        async with (await get_connection()) as conn:
            await conn.execute(
                "INSERT INTO users (discord_id, ign, union_name) VALUES ($1, $2, $3) "
                "ON CONFLICT (discord_id) DO UPDATE SET ign = $2, union_name = $3",
                str(user.id), ign, user_union
            )
        await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")

    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union.")
    @app_commands.check(is_admin_or_mod)
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        async with (await get_connection()) as conn:
            await conn.execute("INSERT INTO union_roles (role_id) VALUES ($1) ON CONFLICT DO NOTHING", str(role.id))
        await interaction.response.send_message(f"✅ Role {role.name} has been registered as a union.")

    @app_commands.command(name="deregister_role_as_union", description="Deregister a Discord role from being a union.")
    @app_commands.check(is_admin_or_mod)
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        async with (await get_connection()) as conn:
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", str(role.id))
        await interaction.response.send_message(f"❌ Role {role.name} has been deregistered as a union.")

    @app_commands.command(name="appoint_union_leader", description="Appoint a user as a union leader.")
    @app_commands.check(is_admin_or_mod)
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        role = discord.utils.get(interaction.guild.roles, name="Union Leader")
        if role:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ {user.mention} has been appointed as a Union Leader.")
        else:
            await interaction.response.send_message("❌ 'Union Leader' role not found.", ephemeral=True)

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a user from being a union leader.")
    @app_commands.check(is_admin_or_mod)
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        role = discord.utils.get(interaction.guild.roles, name="Union Leader")
        if role:
            await user.remove_roles(role)
            await interaction.response.send_message(f"✅ {user.mention} has been dismissed from being a Union Leader.")
        else:
            await interaction.response.send_message("❌ 'Union Leader' role not found.", ephemeral=True)

    @app_commands.command(name="add_user_to_union", description="Assign a user to your union.")
    @app_commands.check(is_union_leader)
    async def add_user_to_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_union = await self.get_user_union(interaction.user.id)
        if not leader_union:
            await interaction.response.send_message("❌ You must be assigned to a union to add users.", ephemeral=True)
            return
        async with (await get_connection()) as conn:
            await conn.execute(
                "INSERT INTO users (discord_id, union_name) VALUES ($1, $2) "
                "ON CONFLICT (discord_id) DO UPDATE SET union_name = $2",
                str(user.id), leader_union
            )
        await interaction.response.send_message(f"✅ {user.mention} has been assigned to the union `{leader_union}`.")

    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union.")
    @app_commands.check(is_union_leader)
    async def remove_user_from_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_union = await self.get_user_union(interaction.user.id)
        target_union = await self.get_user_union(user.id)
        if leader_union != target_union:
            await interaction.response.send_message("❌ You can only remove users from your own union.", ephemeral=True)
            return
        async with (await get_connection()) as conn:
            await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", str(user.id))
        await interaction.response.send_message(f"✅ {user.mention} has been removed from the union `{leader_union}`.")

    @app_commands.command(name="search_user", description="Search for a user’s IGN and union by IGN or Discord name.")
    async def search_user(self, interaction: discord.Interaction, query: str):
        async with (await get_connection()) as conn:
            row = await conn.fetchrow(
                "SELECT ign, union_name FROM users WHERE ign ILIKE $1 OR discord_id = $2",
                f"%{query}%", str(interaction.user.id)
            )
            if not row:
                await interaction.response.send_message("❌ User not found.")
                return
            message = (
                f"**Discord:** {interaction.user.mention}
"
                f"**IGN:** {row['ign'] or 'Not registered'}
"
                f"**Union:** {row['union_name'] or 'Not assigned'}"
            )
            await interaction.response.send_message(message)

    @app_commands.command(name="show_union_detail", description="Show all union roles and their member count.")
    async def show_union_detail(self, interaction: discord.Interaction):
        async with (await get_connection()) as conn:
            rows = await conn.fetch("SELECT role_id FROM union_roles")
            if not rows:
                await interaction.response.send_message("❌ No union roles registered.")
                return
            message = "📋 **Registered Union Roles:**
"
            for row in rows:
                role = interaction.guild.get_role(int(row["role_id"]))
                if role:
                    message += f"- {role.name} ({len(role.members)} members)
"
        await interaction.response.send_message(message)

async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

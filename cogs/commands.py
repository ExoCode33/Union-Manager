import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /register_ign
    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(discord_id="The Discord ID of the user", ign="The IGN to register")
    async def register_ign(self, interaction: discord.Interaction, discord_id: str, ign: str):
        user_id = int(discord_id)
        async with await get_connection() as conn:
            await conn.execute(
                "INSERT INTO users (discord_id, ign) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET ign = $2",
                user_id, ign
            )
        await interaction.response.send_message(f"✅ IGN for <@{discord_id}> set to `{ign}`", ephemeral=True)

    # /search_user
    @app_commands.command(name="search_user", description="Search for a user by Discord ID")
    @app_commands.describe(discord_id="The Discord ID of the user to search")
    async def search_user(self, interaction: discord.Interaction, discord_id: str):
        user_id = int(discord_id)
        async with await get_connection() as conn:
            user = await conn.fetchrow("SELECT ign FROM users WHERE discord_id = $1", user_id)

        if user:
await interaction.response.send_message(f"**Discord:** <@{discord_id}>")
**IGN:** `{user['ign']}`", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ No IGN found for this user.", ephemeral=True)

    # /register_role_as_union
    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union")
    @app_commands.describe(role="The Discord role to register as a union")
    async def register_union_role(self, interaction: discord.Interaction, role: discord.Role):
        async with await get_connection() as conn:
            await conn.execute(
                "INSERT INTO unions (role_id, name) VALUES ($1, $2) ON CONFLICT (role_id) DO NOTHING",
                str(role.id), role.name
            )
        await interaction.response.send_message(f"✅ Registered union: `{role.name}`", ephemeral=True)

    # /deregister_role_as_union
    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role")
    @app_commands.describe(role="The union role to deregister")
    async def deregister_union_role(self, interaction: discord.Interaction, role: discord.Role):
        async with await get_connection() as conn:
            await conn.execute("DELETE FROM unions WHERE role_id = $1", str(role.id))
        await interaction.response.send_message(f"🗑️ Deregistered union: `{role.name}`", ephemeral=True)

    # /appoint_union_leader
    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader")
    @app_commands.describe(user="The user to appoint", role="The union role to assign")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        async with await get_connection() as conn:
            await conn.execute(
                "INSERT INTO leaders (user_id, role_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET role_id = $2",
                str(user.id), str(role.id)
            )
        await interaction.response.send_message(f"👑 `{user.display_name}` appointed as leader of `{role.name}`", ephemeral=True)

    # /dismiss_union_leader
    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader")
    @app_commands.describe(user="The leader to dismiss")
    async def dismiss_union_leader(self, interaction: discord.Interaction, user: discord.Member):
        async with await get_connection() as conn:
            await conn.execute("DELETE FROM leaders WHERE user_id = $1", str(user.id))
        await interaction.response.send_message(f"❌ `{user.display_name}` has been dismissed as a leader.", ephemeral=True)

    # /add_user_to_union
    @app_commands.command(name="add_user_to_union", description="Add a user to your union")
    @app_commands.describe(user="User to add to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_id = str(interaction.user.id)
        async with await get_connection() as conn:
            leader = await conn.fetchrow("SELECT role_id FROM leaders WHERE user_id = $1", leader_id)
            if not leader:
                await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
                return
            await conn.execute("UPDATE users SET role_id = $1 WHERE discord_id = $2", leader['role_id'], str(user.id))
        await user.add_roles(discord.Object(id=int(leader['role_id'])))
        await interaction.response.send_message(f"✅ {user.mention} added to your union.", ephemeral=True)

    # /remove_user_from_union
    @app_commands.command(name="remove_user_from_union", description="Remove a user from your union")
    @app_commands.describe(user="User to remove from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, user: discord.Member):
        leader_id = str(interaction.user.id)
        async with await get_connection() as conn:
            leader = await conn.fetchrow("SELECT role_id FROM leaders WHERE user_id = $1", leader_id)
            if not leader:
                await interaction.response.send_message("❌ You are not a union leader.", ephemeral=True)
                return
            await conn.execute("UPDATE users SET role_id = NULL WHERE discord_id = $1", str(user.id))
        await user.remove_roles(discord.Object(id=int(leader['role_id'])))
        await interaction.response.send_message(f"✅ {user.mention} removed from your union.", ephemeral=True)

    # /show_union_detail
    @app_commands.command(name="show_union_detail", description="Show all registered union roles and member counts")
    async def show_union_detail(self, interaction: discord.Interaction):
        guild = interaction.guild
        async with await get_connection() as conn:
            unions = await conn.fetch("SELECT role_id, name FROM unions")
            members = await conn.fetch("SELECT role_id, COUNT(*) FROM users GROUP BY role_id")

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

        await interaction.response.send_message("
".join(lines), ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionCommands(bot))

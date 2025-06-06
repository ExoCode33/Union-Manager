import discord
from discord import app_commands
from discord.ext import commands
from utils.permissions import is_manager
from utils.db import get_connection

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_union(self, user_id: int):
        conn = await get_connection()
    try:
                row = await conn.fetchrow("SELECT union_name FROM users WHERE discord_id = $1", str(user_id))
                return row["union_name"] if row else None
    finally:
        await conn.close()
    def is_leader_of(self, user_id: str, target_union: str, leaders):
        for row in leaders:
            if row["leader_id"] == user_id and row["role_name"].lower() == target_union.lower():
                return True
        return False

    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(user="The user", ign="In-game name")
    async def register_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        user_union = await self.get_user_union(user.id)
        if not is_manager(interaction.user) and not await self.can_manage(interaction.user.id, user_union):
            await interaction.response.send_message("❌ You can't register IGN for this user.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute(
                    "INSERT INTO users (discord_id, ign, union_name) VALUES ($1, $2, $3) ON CONFLICT (discord_id) DO UPDATE SET ign = $2",
                    str(user.id), ign, user_union)
            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
    finally:
        await conn.close()
    @app_commands.command(name="unregister_ign", description="Remove a user's IGN")
    @app_commands.describe(user="The user")
    async def unregister_ign(self, interaction: discord.Interaction, user: discord.Member):
        user_union = await self.get_user_union(user.id)
        if not is_manager(interaction.user) and not await self.can_manage(interaction.user.id, user_union):
            await interaction.response.send_message("❌ You can't unregister IGN for this user.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute("UPDATE users SET ign = NULL WHERE discord_id = $1", str(user.id))
            await interaction.response.send_message(f"✅ IGN removed for {user.mention}.")
    finally:
        await conn.close()
    @app_commands.command(name="set_union", description="Assign a user to a union")
    @app_commands.describe(user="The user", role="Union role")
    async def set_union(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if not is_manager(interaction.user) and not await self.can_manage(interaction.user.id, role.name):
            await interaction.response.send_message("❌ You can't assign this user to that union.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute(
                    "INSERT INTO users (discord_id, ign, union_name) VALUES ($1, '', $2) ON CONFLICT (discord_id) DO UPDATE SET union_name = $2",
                    str(user.id), role.name)
            try:
                await user.add_roles(role)
            except discord.Forbidden:
                await interaction.followup.send("⚠️ Could not assign the role. Check bot permissions.", ephemeral=True)
            await interaction.response.send_message(f"✅ {user.mention} assigned to **{role.name}**.")
    finally:
        await conn.close()
    @app_commands.command(name="unset_union", description="Remove a user from their union")
    @app_commands.describe(user="The user to remove")
    async def unset_union(self, interaction: discord.Interaction, user: discord.Member):
        union_name = await self.get_user_union(user.id)
        if not union_name:
            await interaction.response.send_message("ℹ️ User is not assigned to any union.", ephemeral=True)
            return
        if not is_manager(interaction.user) and not await self.can_manage(interaction.user.id, union_name):
            await interaction.response.send_message("❌ You can't remove this user from their union.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", str(user.id))
            role = discord.utils.get(interaction.guild.roles, name=union_name)
            if role:
                try:
                    await user.remove_roles(role)
                except discord.Forbidden:
                    await interaction.followup.send("⚠️ Could not remove the role. Check bot permissions.", ephemeral=True)
            await interaction.response.send_message(f"✅ {user.mention} removed from **{union_name}**.")
    finally:
        await conn.close()
    @app_commands.command(name="register_union_role", description="Register a role as a union")
    @app_commands.describe(role="The role to register")
    async def register_union_role(self, interaction: discord.Interaction, role: discord.Role):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can register union roles.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute("INSERT INTO union_roles (role_name) VALUES ($1) ON CONFLICT DO NOTHING", role.name)
            await interaction.response.send_message(f"✅ Union role **{role.name}** registered.")
    finally:
        await conn.close()
    

    @app_commands.command(name="deregister_union_role", description="Remove a registered union role")
    @app_commands.describe(role_name="Union role name")
    async def deregister_union_role(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can deregister union roles.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute("DELETE FROM union_roles WHERE role_name = $1", role_name)
            await interaction.response.send_message(f"🗑️ Union role **{role_name}** has been removed.")
    finally:
        await conn.close()
    @app_commands.command(name="appoint_union_leader", description="Assign a leader to a union role")
    @app_commands.describe(user="The leader", role="The union role")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can appoint union leaders.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute(
                    "INSERT INTO union_leaders (role_name, leader_id) VALUES ($1, $2) ON CONFLICT (role_name) DO UPDATE SET leader_id = EXCLUDED.leader_id",
                    role.name, str(user.id))
            await interaction.response.send_message(f"👑 {user.mention} is now the leader of **{role.name}**.")
    finally:
        await conn.close()
    @app_commands.command(name="dismiss_union_leader", description="Remove the leader of a union")
    @app_commands.describe(role_name="Union role name")
    async def dismiss_union_leader(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can dismiss union leaders.", ephemeral=True)
            return
        conn = await get_connection()
    try:
                await conn.execute("DELETE FROM union_leaders WHERE role_name = $1", role_name)
            await interaction.response.send_message(f"✅ Leader for union **{role_name}** dismissed.")
    finally:
        await conn.close()
    @app_commands.command(name="show_user", description="Show a user's IGN and union")
    @app_commands.describe(user="The user")
    async def show_user(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
    try:
                row = await conn.fetchrow("SELECT ign, union_name FROM users WHERE discord_id = $1", str(user.id))
            if not row:
                await interaction.response.send_message("❌ User not found.")
            else:
                ign = row["ign"] or "-"
                union = row["union_name"] or "-"
                await interaction.response.send_message(f"🧾 {user.mention} → IGN: `{ign}`, Union: `{union}`")
    finally:
        await conn.close()
    @app_commands.command(name="list_union_roles", description="List all registered union roles with member count")
    @app_commands.describe(show_members="Show members and their IGN")
    async def list_union_roles(self, interaction: discord.Interaction, show_members: bool = False):
        try:
            conn = await get_connection()
    try:
                    all_roles = await conn.fetch("SELECT role_name FROM union_roles")
                    counts = await conn.fetch("SELECT union_name, COUNT(*) FROM users WHERE union_name IS NOT NULL GROUP BY union_name")
                    members_by_union = {}
                    if show_members:
                        members = await conn.fetch("SELECT discord_id, ign, union_name FROM users WHERE union_name IS NOT NULL")
                        for row in members:
                            members_by_union.setdefault(row["union_name"], []).append((row["discord_id"], row["ign"]))
    finally:
        await conn.close()
            if not all_roles:
                await interaction.response.send_message("📭 No union roles registered.")
                return
            lines = []
            count_map = {r["union_name"]: r["count"] for r in counts}
            for r in all_roles:
                role = r["role_name"]
                count = count_map.get(role, 0)
                status = "✅" if count >= 30 else ""
                lines.append(f"📋 **{role}** — {count}/30 members {status}")
                if show_members and role in members_by_union:
                    for discord_id, ign in members_by_union[role]:
                        ign_display = ign or "-"
                        lines.append(f"• <@{discord_id}> — IGN: `{ign_display}`")
            await interaction.response.send_message("\n".join(lines))
        except Exception as e:
            print("ERROR:", e)
            await interaction.response.send_message("⚠️ Failed to list union roles.", ephemeral=True)

    @app_commands.command(name="list_union_leaders", description="List all union leaders")
    async def list_union_leaders(self, interaction: discord.Interaction):
        conn = await get_connection()
    try:
                rows = await conn.fetch("SELECT role_name, leader_id FROM union_leaders")
            if not rows:
                await interaction.response.send_message("📭 No union leaders assigned.")
                return
            lines = [f"👑 **{row['role_name']}** → <@{row['leader_id']}>" for row in rows]
            await interaction.response.send_message("\n".join(lines))
    finally:
        await conn.close()
    @app_commands.command(name="search_user", description="Search for a user by IGN or Discord name")
    @app_commands.describe(query="IGN or part of Discord name")
    async def search_user(self, interaction: discord.Interaction, query: str):
        query = query.lower()
        conn = await get_connection()
    try:
                all_users = await conn.fetch("SELECT discord_id, ign, union_name FROM users")
            matched = []
            for row in all_users:
                member = interaction.guild.get_member(int(row["discord_id"]))
                if (row["ign"] and query in row["ign"].lower()) or (member and query in member.display_name.lower()):
                    ign = row["ign"] or "-"
                    union = row["union_name"] or "-"
                    matched.append(f"🔍 {member.mention if member else row['discord_id']} → IGN: `{ign}`, Union: `{union}`")
            if matched:
                await interaction.response.send_message("\n".join(matched[:10]))
            else:
                await interaction.response.send_message("🔎 No matching users found.")
    finally:
        await conn.close()

    async def can_manage(self, user_id, union_name):
        conn = await get_connection()
    try:
                rows = await conn.fetch("SELECT * FROM union_leaders")
            return self.is_leader_of(str(user_id), union_name, rows)
    finally:
        await conn.close()
async def setup(bot):
    await bot.add_cog(BotCommands(bot))

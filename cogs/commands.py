import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from utils.permissions import is_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database.db")

def can_manage_union(user: discord.Member, target_union: str) -> bool:
    if is_manager(user):
        return True
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT role_name FROM union_leaders WHERE leader_id = ?", (str(user.id),))
        result = cursor.fetchone()
        conn.close()
        return result and result[0].lower() == target_union.lower()
    except Exception as e:
        print(f"Permission check error: {e}")
        return False

class BotCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(user="The Discord user", ign="Their in-game name")
    async def register_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        if not is_manager(interaction.user) and not can_manage_union(interaction.user, self.get_user_union(user.id)):
            await interaction.response.send_message("❌ You don't have permission to register IGN for this user.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign) VALUES (?, ?)", (str(user.id), ign))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {user.mention}'s IGN registered as `{ign}`.")

    @app_commands.command(name="unregister_ign", description="Remove a user's IGN")
    @app_commands.describe(user="The Discord user")
    async def unregister_ign(self, interaction: discord.Interaction, user: discord.Member):
        if not is_manager(interaction.user) and not can_manage_union(interaction.user, self.get_user_union(user.id)):
            await interaction.response.send_message("❌ You don't have permission to unregister IGN for this user.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET ign = NULL WHERE discord_id = ?", (str(user.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {user.mention}'s IGN has been removed.")

    @app_commands.command(name="set_union", description="Assign a user to a union")
    @app_commands.describe(user="The user to assign", union="Union name (must be a role)")
    async def set_union(self, interaction: discord.Interaction, user: discord.Member, union: str):
        if not is_manager(interaction.user) and not can_manage_union(interaction.user, union):
            await interaction.response.send_message("❌ You can't manage this union.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET union_name = ? WHERE discord_id = ?", (union, str(user.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {user.mention} assigned to `{union}`.")

    @app_commands.command(name="unset_union", description="Remove a user from their union")
    @app_commands.describe(user="The user to remove")
    async def unset_union(self, interaction: discord.Interaction, user: discord.Member):
        if not is_manager(interaction.user) and not can_manage_union(interaction.user, self.get_user_union(user.id)):
            await interaction.response.send_message("❌ You can't manage this union.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (str(user.id),))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {user.mention} has been removed from their union.")

    @app_commands.command(name="register_union_role", description="Register a role as a union")
    @app_commands.describe(role_name="Name of the union role")
    async def register_union_role(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can do that.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO union_roles (role_name) VALUES (?)", (role_name,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Union role `{role_name}` registered.")

    @app_commands.command(name="deregister_union_role", description="Remove a registered union role")
    @app_commands.describe(role_name="Name of the union role")
    async def deregister_union_role(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can do that.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM union_roles WHERE role_name = ?", (role_name,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Union role `{role_name}` deregistered.")

    @app_commands.command(name="appoint_union_leader", description="Assign a user as leader of a union")
    @app_commands.describe(user="The new leader", role_name="Union role they lead")
    async def appoint_union_leader(self, interaction: discord.Interaction, user: discord.Member, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can assign leaders.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO union_leaders (role_name, leader_id) VALUES (?, ?)", (role_name, str(user.id)))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {user.mention} appointed as leader of `{role_name}`.")

    @app_commands.command(name="dismiss_union_leader", description="Remove a union leader")
    @app_commands.describe(role_name="Union role")
    async def dismiss_union_leader(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ Only Admin or Mod can dismiss leaders.", ephemeral=True)
            return
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM union_leaders WHERE role_name = ?", (role_name,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ Leader for `{role_name}` has been dismissed.")

    @app_commands.command(name="list_union_roles", description="List all registered union roles with member count")
    @app_commands.describe(show_members="Also display members and their IGN")
    async def list_union_roles(self, interaction: discord.Interaction, show_members: bool = False):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT role_name FROM union_roles")
            all_roles = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT union_name, COUNT(*) FROM users WHERE union_name IS NOT NULL GROUP BY union_name")
            counts = {row[0]: row[1] for row in cursor.fetchall()}
            members_by_union = {}
            if show_members:
                cursor.execute("SELECT discord_id, ign, union_name FROM users WHERE union_name IS NOT NULL")
                for discord_id, ign, union_name in cursor.fetchall():
                    if union_name not in members_by_union:
                        members_by_union[union_name] = []
                    members_by_union[union_name].append((discord_id, ign))
            conn.close()
            if not all_roles:
                await interaction.response.send_message("📭 No union roles registered.")
                return
            lines = []
            for role in all_roles:
                count = counts.get(role, 0)
                status = "✅" if count >= 30 else ""
                lines.append(f"📋 `{role}` — {count}/30 members {status}")
                if show_members and role in members_by_union:
                    for member_id, ign in members_by_union[role]:
                        ign_display = ign if ign else "-"
                        lines.append(f"• <@{member_id}> — IGN: `{ign_display}`")
            await interaction.response.send_message("\n".join(lines))
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to list union roles.", ephemeral=True)

    def get_user_union(self, user_id: int):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT union_name FROM users WHERE discord_id = ?", (str(user_id),))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

async def setup(bot):
    await bot.add_cog(BotCommands(bot))

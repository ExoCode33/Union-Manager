import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionMembership(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return sqlite3.connect("database.db")

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    def get_user_led_union(self, user_id):
        """Get the union that this user leads"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT role_name FROM union_leaders WHERE leader_id = ?", (str(user_id),))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    @app_commands.command(name="add_user_to_union", description="Add user to YOUR union (auto-detects your union)")
    @app_commands.describe(username="User to add to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, username: discord.Member):
        # Check if user is a union leader
        led_union = self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Add user to the leader's union
            cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign_primary, ign_secondary, union_name) VALUES (?, COALESCE((SELECT ign_primary FROM users WHERE discord_id = ?), NULL), COALESCE((SELECT ign_secondary FROM users WHERE discord_id = ?), NULL), ?)", 
                         (str(username.id), str(username.id), str(username.id), led_union))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} added to your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove user from YOUR union")
    @app_commands.describe(username="User to remove from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, username: discord.Member):
        # Check if user is a union leader
        led_union = self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if user is in the leader's union
            cursor.execute("SELECT union_name FROM users WHERE discord_id = ?", (str(username.id),))
            result = cursor.fetchone()
            
            if not result or result[0] != led_union:
                await interaction.response.send_message(f"❌ {username.mention} is not in your union **{led_union}**", ephemeral=True)
                return

            cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} removed from your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="admin_add_user_to_union", description="Add user to ANY union (Admin override)")
    @app_commands.describe(username="User to add", role="Union role to add them to")
    async def admin_add_user_to_union(self, interaction: discord.Interaction, username: discord.Member, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if role is registered as union
            cursor.execute("SELECT role_name FROM union_roles WHERE role_name = ?", (role.name,))
            if not cursor.fetchone():
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign_primary, ign_secondary, union_name) VALUES (?, COALESCE((SELECT ign_primary FROM users WHERE discord_id = ?), NULL), COALESCE((SELECT ign_secondary FROM users WHERE discord_id = ?), NULL), ?)", 
                         (str(username.id), str(username.id), str(username.id), role.name))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} added to union **{role.name}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="admin_remove_user_from_union", description="Remove user from ANY union (Admin override)")
    @app_commands.describe(username="User to remove from their union")
    async def admin_remove_user_from_union(self, interaction: discord.Interaction, username: discord.Member):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT union_name FROM users WHERE discord_id = ?", (str(username.id),))
            result = cursor.fetchone()
            
            if not result or not result[0]:
                await interaction.response.send_message(f"❌ {username.mention} is not in any union.", ephemeral=True)
                return

            union_name = result[0]
            cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} removed from union **{union_name}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

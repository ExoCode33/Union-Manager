import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return sqlite3.connect("database.db")

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union (Admin only)")
    @app_commands.describe(role="Discord role to register as union")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        if not role.name.startswith("Union-"):
            await interaction.response.send_message("❌ Role name must start with 'Union-' prefix.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT OR IGNORE INTO union_roles (role_name) VALUES (?)", (role.name,))
            if cursor.rowcount > 0:
                conn.commit()
                await interaction.response.send_message(f"✅ Role **{role.name}** registered as union", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Role **{role.name}** is already registered as union", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering union role: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role (Admin only)")
    @app_commands.describe(role="Discord role to deregister")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Remove from union_roles
            cursor.execute("DELETE FROM union_roles WHERE role_name = ?", (role.name,))
            # Remove leader assignment
            cursor.execute("DELETE FROM union_leaders WHERE role_name = ?", (role.name,))
            # Remove users from this union
            cursor.execute("UPDATE users SET union_name = NULL WHERE union_name = ?", (role.name,))
            
            if cursor.rowcount > 0:
                conn.commit()
                await interaction.response.send_message(f"✅ Union **{role.name}** deregistered and all members removed", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Role **{role.name}** was not registered as union", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deregistering union role: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader (Admin only)")
    @app_commands.describe(username="User to appoint as leader", role="Union role")
    async def appoint_union_leader(self, interaction: discord.Interaction, username: discord.Member, role: discord.Role):
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

            cursor.execute("INSERT OR REPLACE INTO union_leaders (role_name, leader_id) VALUES (?, ?)", 
                         (role.name, str(username.id)))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} appointed as leader of **{role.name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error appointing union leader: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader (Admin only)")
    @app_commands.describe(role="Union role to dismiss leader from")
    async def dismiss_union_leader(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM union_leaders WHERE role_name = ?", (role.name,))
            if cursor.rowcount > 0:
                conn.commit()
                await interaction.response.send_message(f"✅ Leader dismissed from **{role.name}**", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ No leader found for **{role.name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error dismissing union leader: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionManagement(bot))

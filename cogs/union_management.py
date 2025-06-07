import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_connection(self):
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    async def find_user_by_ign(self, ign):
        """Find Discord user by their primary or secondary IGN"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Check both primary and secondary IGN
            cursor.execute(
                "SELECT discord_id FROM users WHERE ign_primary = ? OR ign_secondary = ?", 
                (ign, ign)
            )
            row = cursor.fetchone()
            return row['discord_id'] if row else None
        finally:
            conn.close()

    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union (Admin only)")
    @app_commands.describe(role="Discord role to register as union")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        if not role.name.startswith("Union-"):
            await interaction.response.send_message("❌ Role name must start with 'Union-' prefix.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT OR IGNORE INTO union_roles (role_name) VALUES (?)", (role.name,))
            conn.commit()
            
            if cursor.rowcount > 0:
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

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM union_roles WHERE role_name = ?", (role.name,))
            cursor.execute("DELETE FROM union_leaders WHERE role_name = ?", (role.name,))
            cursor.execute("UPDATE users SET union_name = NULL WHERE union_name = ?", (role.name,))
            conn.commit()
            await interaction.response.send_message(f"✅ Union **{role.name}** deregistered and all members removed", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deregistering union role: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader by IGN (Admin only)")
    @app_commands.describe(ign="In-game name of the player to appoint as leader", role="Union role")
    async def appoint_union_leader(self, interaction: discord.Interaction, ign: str, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        # Find Discord user by IGN
        discord_id = await self.find_user_by_ign(ign)
        if not discord_id:
            await interaction.response.send_message(
                f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first using `/register_ign`.", 
                ephemeral=True
            )
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if role is registered as union
            cursor.execute("SELECT role_name FROM union_roles WHERE role_name = ?", (role.name,))
            if not cursor.fetchone():
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Get the Discord user object for display
            try:
                discord_user = await self.bot.fetch_user(int(discord_id))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {discord_id}"

            # Insert/update union leader
            cursor.execute("""
                INSERT OR REPLACE INTO union_leaders (role_name, leader_id)
                VALUES (?, ?)
            """, (role.name, discord_id))
            conn.commit()

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) appointed as leader of **{role.name}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error appointing union leader: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader by IGN (Admin only)")
    @app_commands.describe(ign="In-game name of the leader to dismiss", role="Union role to dismiss leader from")
    async def dismiss_union_leader(self, interaction: discord.Interaction, ign: str, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        # Find Discord user by IGN
        discord_id = await self.find_user_by_ign(ign)
        if not discord_id:
            await interaction.response.send_message(
                f"❌ No Discord user found with IGN **{ign}**.", 
                ephemeral=True
            )
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Check if this user is actually the leader of this union
            cursor.execute("SELECT leader_id FROM union_leaders WHERE role_name = ?", (role.name,))
            current_leader = cursor.fetchone()
            
            if not current_leader:
                await interaction.response.send_message(f"❌ No leader found for **{role.name}**", ephemeral=True)
                return
                
            if current_leader['leader_id'] != discord_id:
                await interaction.response.send_message(
                    f"❌ **{ign}** is not the leader of **{role.name}**", 
                    ephemeral=True
                )
                return

            # Get the Discord user object for display
            try:
                discord_user = await self.bot.fetch_user(int(discord_id))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {discord_id}"

            # Remove the leader
            cursor.execute("DELETE FROM union_leaders WHERE role_name = ? AND leader_id = ?", (role.name, discord_id))
            conn.commit()
            
            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) dismissed as leader of **{role.name}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error dismissing union leader: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="check_ign_binding", description="Check which Discord user an IGN is bound to (Admin only)")
    @app_commands.describe(ign="In-game name to check")
    async def check_ign_binding(self, interaction: discord.Interaction, ign: str):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT discord_id, ign_primary, ign_secondary FROM users WHERE ign_primary = ? OR ign_secondary = ?", 
                (ign, ign)
            )
            row = cursor.fetchone()
            
            if not row:
                await interaction.response.send_message(f"❌ No Discord user found with IGN **{ign}**", ephemeral=True)
                return

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            ign_type = "Primary" if row['ign_primary'] == ign else "Secondary"
            
            await interaction.response.send_message(
                f"✅ IGN **{ign}** is bound to {user_display}\n"
                f"**Type:** {ign_type} IGN\n"
                f"**Primary IGN:** {row['ign_primary'] or 'Not set'}\n"
                f"**Secondary IGN:** {row['ign_secondary'] or 'Not set'}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error checking IGN binding: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionManagement(bot))

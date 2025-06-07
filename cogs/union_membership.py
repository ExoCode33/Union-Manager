import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionMembership(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_connection(self):
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    async def get_user_led_union(self, user_id):
        """Get the union this user leads"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT role_name FROM union_leaders WHERE leader_id = ?", (str(user_id),))
            row = cursor.fetchone()
            return row['role_name'] if row else None
        finally:
            conn.close()

    @app_commands.command(name="add_user_to_union", description="Add user to YOUR union (auto-detects your union)")
    @app_commands.describe(username="User to add to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, username: discord.Member):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Get existing IGNs if user already exists
            cursor.execute("SELECT ign_primary, ign_secondary FROM users WHERE discord_id = ?", (str(username.id),))
            existing = cursor.fetchone()
            
            ign_primary = existing['ign_primary'] if existing else None
            ign_secondary = existing['ign_secondary'] if existing else None
            
            cursor.execute("""
                INSERT OR REPLACE INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (?, ?, ?, ?)
            """, (str(username.id), ign_primary, ign_secondary, led_union))
            conn.commit()

            await interaction.response.send_message(f"✅ {username.mention} added to your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove user from YOUR union")
    @app_commands.describe(username="User to remove from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, username: discord.Member):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT union_name FROM users WHERE discord_id = ?", (str(username.id),))
            row = cursor.fetchone()
            
            if not row or row['union_name'] != led_union:
                await interaction.response.send_message(f"❌ {username.mention} is not in your union **{led_union}**", ephemeral=True)
                return

            cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} removed from your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="add_user_to_union_by_ign", description="Add user to YOUR union by their IGN")
    @app_commands.describe(ign="In-game name of the user to add")
    async def add_user_to_union_by_ign(self, interaction: discord.Interaction, ign: str):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Find user by IGN (primary or secondary)
            cursor.execute(
                "SELECT discord_id, ign_primary, ign_secondary FROM users WHERE ign_primary = ? OR ign_secondary = ?", 
                (ign, ign)
            )
            row = cursor.fetchone()
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first.", 
                    ephemeral=True
                )
                return

            # Update their union
            cursor.execute("UPDATE users SET union_name = ? WHERE discord_id = ?", (led_union, row['discord_id']))
            conn.commit()

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to your union **{led_union}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="remove_user_from_union_by_ign", description="Remove user from YOUR union by their IGN")
    @app_commands.describe(ign="In-game name of the user to remove")
    async def remove_user_from_union_by_ign(self, interaction: discord.Interaction, ign: str):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # Find user by IGN and check if they're in our union
            cursor.execute(
                "SELECT discord_id, union_name FROM users WHERE (ign_primary = ? OR ign_secondary = ?) AND union_name = ?", 
                (ign, ign, led_union)
            )
            row = cursor.fetchone()
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No user with IGN **{ign}** found in your union **{led_union}**", 
                    ephemeral=True
                )
                return

            # Remove from union
            cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (row['discord_id'],))
            conn.commit()

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from your union **{led_union}**", 
                ephemeral=True
            )
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

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT role_name FROM union_roles WHERE role_name = ?", (role.name,))
            if not cursor.fetchone():
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Get existing IGNs if user already exists
            cursor.execute("SELECT ign_primary, ign_secondary FROM users WHERE discord_id = ?", (str(username.id),))
            existing = cursor.fetchone()
            
            ign_primary = existing['ign_primary'] if existing else None
            ign_secondary = existing['ign_secondary'] if existing else None

            cursor.execute("""
                INSERT OR REPLACE INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (?, ?, ?, ?)
            """, (str(username.id), ign_primary, ign_secondary, role.name))
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

        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT union_name FROM users WHERE discord_id = ?", (str(username.id),))
            row = cursor.fetchone()
            
            if not row or not row['union_name']:
                await interaction.response.send_message(f"❌ {username.mention} is not in any union.", ephemeral=True)
                return

            cursor.execute("UPDATE users SET union_name = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            await interaction.response.send_message(f"✅ {username.mention} removed from union **{row['union_name']}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

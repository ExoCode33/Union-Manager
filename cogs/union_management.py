import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    async def find_user_by_ign(self, ign):
        """Find Discord user by their primary or secondary IGN"""
        conn = await get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT discord_id FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            return row['discord_id'] if row else None
        finally:
            await conn.close()

    @app_commands.command(name="register_role_as_union", description="Register a Discord role as a union (Admin only)")
    @app_commands.describe(role="Discord role to register as union")
    async def register_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        if not role.name.startswith("Union-"):
            await interaction.response.send_message("❌ Role name must start with 'Union-' prefix.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            result = await conn.execute("INSERT INTO union_roles (role_id) VALUES ($1) ON CONFLICT DO NOTHING", role.id)
            if result == "INSERT 0 1":
                await interaction.response.send_message(f"✅ Role **{role.name}** registered as union", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Role **{role.name}** is already registered as union", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering union role: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role (Admin only)")
    @app_commands.describe(role="Discord role to deregister")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", role.id)
            await conn.execute("DELETE FROM union_leaders WHERE role_id = $1", role.id)
            await conn.execute("UPDATE users SET union_name = NULL WHERE union_name = $1", str(role.id))
            await interaction.response.send_message(f"✅ Union **{role.name}** deregistered and all members removed", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deregistering union role: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

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

        conn = await get_connection()
        try:
            # Check if role is registered as union
            role_check = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Get the Discord user object for display
            try:
                discord_user = await self.bot.fetch_user(int(discord_id))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {discord_id}"

            # Insert/update union leader
            await conn.execute("""
                INSERT INTO union_leaders (role_id, leader_id)
                VALUES ($1, $2)
                ON CONFLICT (role_id) DO UPDATE SET leader_id = EXCLUDED.leader_id
            """, role.id, discord_id)

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) appointed as leader of **{role.name}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error appointing union leader: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

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

        conn = await get_connection()
        try:
            # Check if this user is actually the leader of this union
            current_leader = await conn.fetchrow("SELECT leader_id FROM union_leaders WHERE role_id = $1", role.id)
            
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
            await conn.execute("DELETE FROM union_leaders WHERE role_id = $1 AND leader_id = $2", role.id, discord_id)
            
            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) dismissed as leader of **{role.name}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error dismissing union leader: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionManagement(bot))

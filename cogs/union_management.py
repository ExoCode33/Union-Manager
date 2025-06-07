import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        conn = await get_connection()
        try:
            result = await conn.execute("INSERT INTO union_roles (role_name) VALUES ($1) ON CONFLICT DO NOTHING", role.name)
            if result and "INSERT 0 1" in result:
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
            await conn.execute("DELETE FROM union_roles WHERE role_name = $1", role.name)
            await conn.execute("DELETE FROM union_leaders WHERE role_name = $1", role.name)
            await conn.execute("UPDATE users SET union_name = NULL WHERE union_name = $1", role.name)
            await interaction.response.send_message(f"✅ Union **{role.name}** deregistered and all members removed", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deregistering union role: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader (Admin only)")
    @app_commands.describe(username="User to appoint as leader", role="Union role")
    async def appoint_union_leader(self, interaction: discord.Interaction, username: discord.Member, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT role_name FROM union_roles WHERE role_name = $1", role.name)
            if not row:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            await conn.execute("""
                INSERT INTO union_leaders (role_name, leader_id)
                VALUES ($1, $2)
                ON CONFLICT (role_name) DO UPDATE SET leader_id = EXCLUDED.leader_id
            """, role.name, str(username.id))

            await interaction.response.send_message(f"✅ {username.mention} appointed as leader of **{role.name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error appointing union leader: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="dismiss_union_leader", description="Dismiss a union leader (Admin only)")
    @app_commands.describe(role="Union role to dismiss leader from")
    async def dismiss_union_leader(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            result = await conn.execute("DELETE FROM union_leaders WHERE role_name = $1", role.name)
            if result and "DELETE 1" in result:
                await interaction.response.send_message(f"✅ Leader dismissed from **{role.name}**", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ No leader found for **{role.name}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error dismissing union leader: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionManagement(bot))

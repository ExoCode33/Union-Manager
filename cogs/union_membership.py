import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class UnionMembership(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_admin_role(self, member):
        return any(role.name.lower() == "admin" for role in member.roles)

    async def get_user_led_union(self, user_id):
        """Get the union this user leads"""
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT role_name FROM union_leaders WHERE leader_id = $1", str(user_id))
            return row['role_name'] if row else None
        finally:
            await conn.close()

    @app_commands.command(name="add_user_to_union", description="Add user to YOUR union (auto-detects your union)")
    @app_commands.describe(username="User to add to your union")
    async def add_user_to_union(self, interaction: discord.Interaction, username: discord.Member):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (
                    $1,
                    (SELECT ign_primary FROM users WHERE discord_id = $1),
                    (SELECT ign_secondary FROM users WHERE discord_id = $1),
                    $2
                )
                ON CONFLICT (discord_id) DO UPDATE SET union_name = EXCLUDED.union_name
            """, str(username.id), led_union)

            await interaction.response.send_message(f"✅ {username.mention} added to your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove user from YOUR union")
    @app_commands.describe(username="User to remove from your union")
    async def remove_user_from_union(self, interaction: discord.Interaction, username: discord.Member):
        led_union = await self.get_user_led_union(interaction.user.id)
        if not led_union:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT union_name FROM users WHERE discord_id = $1", str(username.id))
            if not row or row['union_name'] != led_union:
                await interaction.response.send_message(f"❌ {username.mention} is not in your union **{led_union}**", ephemeral=True)
                return

            await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", str(username.id))
            await interaction.response.send_message(f"✅ {username.mention} removed from your union **{led_union}**", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="admin_add_user_to_union", description="Add user to ANY union (Admin override)")
    @app_commands.describe(username="User to add", role="Union role to add them to")
    async def admin_add_user_to_union(self, interaction: discord.Interaction, username: discord.Member, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            role_check = await conn.fetchrow("SELECT role_name FROM union_roles WHERE role_name = $1", role.name)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (
                    $1,
                    (SELECT ign_primary FROM users WHERE discord_id = $1),
                    (SELECT ign_secondary FROM users WHERE discord_id = $1),
                    $2
                )
                ON CONFLICT (discord_id) DO UPDATE SET union_name = EXCLUDED.union_name
            """, str(username.id), role.name)

            await interaction.response.send_message(f"✅ {username.mention} added to union **{role.name}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="admin_remove_user_from_union", description="Remove user from ANY union (Admin override)")
    @app_commands.describe(username="User to remove from their union")
    async def admin_remove_user_from_union(self, interaction: discord.Interaction, username: discord.Member):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT union_name FROM users WHERE discord_id = $1", str(username.id))
            if not row or not row['union_name']:
                await interaction.response.send_message(f"❌ {username.mention} is not in any union.", ephemeral=True)
                return

            await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", str(username.id))
            await interaction.response.send_message(f"✅ {username.mention} removed from union **{row['union_name']}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

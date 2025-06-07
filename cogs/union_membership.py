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
        """Get the union role_id this user leads"""
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT role_id FROM union_leaders WHERE user_id = $1", int(user_id))
            return int(row['role_id']) if row else None
        finally:
            await conn.close()

    @app_commands.command(name="add_user_to_union", description="Add user to YOUR union by IGN (auto-detects your union)")
    @app_commands.describe(ign="In-game name of the user to add")
    async def add_user_to_union(self, interaction: discord.Interaction, ign: str):
        led_union_id = await self.get_user_led_union(interaction.user.id)
        if not led_union_id:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        # Get the role name for display
        led_union_role = interaction.guild.get_role(led_union_id)
        led_union_name = led_union_role.name if led_union_role else f"Role ID: {led_union_id}"

        conn = await get_connection()
        try:
            # Find user by IGN (primary or secondary)
            row = await conn.fetchrow(
                "SELECT discord_id, ign_primary, ign_secondary FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first.", 
                    ephemeral=True
                )
                return

            # Update their union (store role_id as string in union_name for compatibility)
            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (discord_id) DO UPDATE SET union_name = EXCLUDED.union_name
            """, row['discord_id'], row['ign_primary'], row['ign_secondary'], str(led_union_id))

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to your union **{led_union_name}**", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove user from YOUR union by IGN")
    @app_commands.describe(ign="In-game name of the user to remove")
    async def remove_user_from_union(self, interaction: discord.Interaction, ign: str):
        led_union_id = await self.get_user_led_union(interaction.user.id)
        if not led_union_id:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=True)
            return

        # Get the role name for display
        led_union_role = interaction.guild.get_role(led_union_id)
        led_union_name = led_union_role.name if led_union_role else f"Role ID: {led_union_id}"

        conn = await get_connection()
        try:
            # Find user by IGN and check if they're in our union
            row = await conn.fetchrow(
                "SELECT discord_id, union_name FROM users WHERE (ign_primary = $1 OR ign_secondary = $1) AND union_name = $2", 
                ign, str(led_union_id)
            )
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No user with IGN **{ign}** found in your union **{led_union_name}**", 
                    ephemeral=True
                )
                return

            # Remove from union
            await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", row['discord_id'])

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from your union **{led_union_name}**", 
                ephemeral=True
            )
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
            role_check = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Get existing IGNs if user already exists
            existing = await conn.fetchrow("SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1", str(username.id))
            
            ign_primary = existing['ign_primary'] if existing else None
            ign_secondary = existing['ign_secondary'] if existing else None

            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (discord_id) DO UPDATE SET union_name = EXCLUDED.union_name
            """, str(username.id), ign_primary, ign_secondary, str(role.id))

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

            # Get role name for display
            try:
                role_id = int(row['union_name'])
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Role ID: {role_id}"
            except:
                role_name = row['union_name']

            await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", str(username.id))
            await interaction.response.send_message(f"✅ {username.mention} removed from union **{role_name}** (Admin override)", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

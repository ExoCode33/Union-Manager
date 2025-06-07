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
        """Get the union role_id this user leads (checks both leadership slots)"""
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT role_id, role_id_2 FROM union_leaders WHERE user_id = $1", int(user_id))
            if row:
                # Return the first non-null leadership role (prioritize role_id)
                return int(row['role_id']) if row['role_id'] else (int(row['role_id_2']) if row['role_id_2'] else None)
            return None
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

            # Update their union (choose appropriate slot)
            await conn.execute("""
                INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2)
                VALUES ($1, $2, $3, $4, $5, NULL)
                ON CONFLICT (discord_id) DO UPDATE SET 
                    union_name = CASE 
                        WHEN users.union_name IS NULL THEN EXCLUDED.union_name
                        WHEN users.union_name_2 IS NULL THEN users.union_name
                        ELSE users.union_name
                    END,
                    union_name_2 = CASE 
                        WHEN users.union_name IS NOT NULL AND users.union_name_2 IS NULL THEN EXCLUDED.union_name
                        ELSE users.union_name_2
                    END
            """, row['discord_id'], led_union_role.name if led_union_role else f"Role {led_union_id}", 
                 row['ign_primary'], row['ign_secondary'], str(led_union_id))

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to your union **{led_union_name}** using {ign_type} IGN", 
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
            # Find user by IGN and check if they're in our union (in the correct slot)
            row = await conn.fetchrow(
                """SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 
                   FROM users 
                   WHERE (ign_primary = $1 OR ign_secondary = $1)""", 
                ign
            )
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No user with IGN **{ign}** found", 
                    ephemeral=True
                )
                return

            # Determine which IGN and union slot we're dealing with
            is_primary_ign = (row['ign_primary'] == ign)
            current_union = row['union_name'] if is_primary_ign else row['union_name_2']
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            # Check if they're in our union in the correct slot
            if str(current_union) != str(led_union_id):
                await interaction.response.send_message(
                    f"❌ **{ign}** is not in your union **{led_union_name}** (checked {ign_type} IGN slot)", 
                    ephemeral=True
                )
                return

            # Remove from the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = NULL WHERE discord_id = $1", row['discord_id'])

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from your union **{led_union_name}** ({ign_type} IGN slot)", 
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

    @app_commands.command(name="admin_remove_user_from_union", description="Remove user from ANY union by IGN (Admin override)")
    @app_commands.describe(ign="In-game name of the user to remove")
    async def admin_remove_user_from_union(self, interaction: discord.Interaction, ign: str):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            # Find user by IGN
            row = await conn.fetchrow(
                "SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not row:
                await interaction.response.send_message(f"❌ No user found with IGN **{ign}**", ephemeral=True)
                return

            # Determine which IGN and union slot we're dealing with
            is_primary_ign = (row['ign_primary'] == ign)
            current_union = row['union_name'] if is_primary_ign else row['union_name_2']
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            if not current_union:
                await interaction.response.send_message(
                    f"❌ **{ign}** ({ign_type} IGN) is not in any union", 
                    ephemeral=True
                )
                return

            # Get role name for display
            try:
                role_id = int(current_union)
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Role ID: {role_id}"
            except:
                role_name = current_union

            # Remove from the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = NULL WHERE discord_id = $1", row['discord_id'])

            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {row['discord_id']}"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from union **{role_name}** ({ign_type} IGN slot) (Admin override)", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

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
                "SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not row:
                await interaction.response.send_message(
                    f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first.", 
                    ephemeral=True
                )
                return

            # Determine which IGN this is and which slot to use
            is_primary_ign = (row['ign_primary'] == ign)
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            # Check if user is already in this union with this IGN
            current_union = row['union_name'] if is_primary_ign else row['union_name_2']
            if str(current_union) == str(led_union_id):
                await interaction.response.send_message(
                    f"❌ **{ign}** is already in your union **{led_union_name}**", 
                    ephemeral=True
                )
                return

            # Update the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = $1 WHERE discord_id = $2", str(led_union_id), row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = $1 WHERE discord_id = $2", str(led_union_id), row['discord_id'])

            # Get Discord user for display and role assignment
            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to assign the role
                try:
                    member = interaction.guild.get_member(int(row['discord_id']))
                    if member:
                        # Assign the Discord role
                        await member.add_roles(led_union_role, reason=f"Added to union via leader command by {interaction.user}")
                        role_status = f" and assigned **@{led_union_name}** Discord role"
                    else:
                        role_status = " (Discord role not assigned - user not in server)"
                except Exception as role_error:
                    role_status = f" (Discord role assignment failed: {str(role_error)})"
                    
            except:
                user_display = f"User ID: {row['discord_id']}"
                role_status = " (Discord role not assigned - user not found)"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to your union **{led_union_name}** using {ign_type} IGN{role_status}", 
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

            # Get Discord user for display and role removal
            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to remove the role
                try:
                    member = interaction.guild.get_member(int(row['discord_id']))
                    if member:
                        # Check if user should still have this role (other IGN might still be in this union)
                        other_union = row['union_name_2'] if is_primary_ign else row['union_name']
                        if str(other_union) == str(led_union_id):
                            # Their other IGN is still in this union, don't remove role
                            role_status = " (Discord role kept - other IGN still in union)"
                        else:
                            # Remove the Discord role
                            await member.remove_roles(led_union_role, reason=f"Removed from union via leader command by {interaction.user}")
                            role_status = f" and removed **@{led_union_name}** Discord role"
                    else:
                        role_status = " (Discord role not removed - user not in server)"
                except Exception as role_error:
                    role_status = f" (Discord role removal failed: {str(role_error)})"
                    
            except:
                user_display = f"User ID: {row['discord_id']}"
                role_status = " (Discord role not removed - user not found)"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from your union **{led_union_name}** ({ign_type} IGN slot){role_status}", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="admin_add_user_to_union", description="Add user to ANY union by IGN (Admin override)")
    @app_commands.describe(ign="In-game name of the user to add", role="Union role to add them to")
    async def admin_add_user_to_union(self, interaction: discord.Interaction, ign: str, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            # Check if role is registered as union
            role_check = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Find user by IGN (primary or secondary)
            user_row = await conn.fetchrow(
                "SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not user_row:
                await interaction.response.send_message(
                    f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first using `/register_primary_ign` or `/register_secondary_ign`.", 
                    ephemeral=True
                )
                return

            # Determine which IGN this is and which slot to use
            is_primary_ign = (user_row['ign_primary'] == ign)
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            # Check if user is already in this union with this IGN
            current_union = user_row['union_name'] if is_primary_ign else user_row['union_name_2']
            if str(current_union) == str(role.id):
                await interaction.response.send_message(
                    f"❌ **{ign}** is already in union **{role.name}**", 
                    ephemeral=True
                )
                return

            # Check if this IGN is already in another union
            if current_union:
                try:
                    current_role = interaction.guild.get_role(int(current_union))
                    current_role_name = current_role.name if current_role else f"Role ID: {current_union}"
                    await interaction.response.send_message(
                        f"❌ **{ign}** ({ign_type} IGN) is already in union **{current_role_name}**. Use `/admin_remove_ign_from_union` first to move them.",
                        ephemeral=True
                    )
                    return
                except:
                    # Invalid role ID in database, proceed with update
                    pass

            # Update the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = $1 WHERE discord_id = $2", str(role.id), user_row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = $1 WHERE discord_id = $2", str(role.id), user_row['discord_id'])

            # Get Discord user for display and role assignment
            try:
                discord_user = await self.bot.fetch_user(int(user_row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to assign the role
                try:
                    member = interaction.guild.get_member(int(user_row['discord_id']))
                    if member:
                        # Assign the Discord role
                        await member.add_roles(role, reason=f"Added to union via admin command by {interaction.user}")
                        role_status = f" and assigned **@{role.name}** Discord role"
                    else:
                        role_status = " (Discord role not assigned - user not in server)"
                except Exception as role_error:
                    role_status = f" (Discord role assignment failed: {str(role_error)})"
                    
            except:
                user_display = f"User ID: {user_row['discord_id']}"
                role_status = " (Discord role not assigned - user not found)"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to union **{role.name}** using {ign_type} IGN{role_status} (Admin override)", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="admin_remove_user_from_union", description="Remove user from specified union by IGN (Admin override)")
    @app_commands.describe(ign="In-game name to remove", role="Union role to remove them from")
    async def admin_remove_user_from_union(self, interaction: discord.Interaction, ign: str, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            # Check if role is registered as union
            role_check = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=True)
                return

            # Find user by IGN and check if they're in the specified union
            row = await conn.fetchrow(
                "SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not row:
                await interaction.response.send_message(f"❌ No user found with IGN **{ign}**", ephemeral=True)
                return

            # Determine which IGN and check if they're in the specified union
            is_primary_ign = (row['ign_primary'] == ign)
            current_union = row['union_name'] if is_primary_ign else row['union_name_2']
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            # Check if they're in the specified union with this IGN
            if str(current_union) != str(role.id):
                # Show which union they're actually in (if any)
                if current_union:
                    try:
                        actual_role = interaction.guild.get_role(int(current_union))
                        actual_union_name = actual_role.name if actual_role else f"Role ID: {current_union}"
                        await interaction.response.send_message(
                            f"❌ **{ign}** ({ign_type} IGN) is not in **{role.name}**.\n"
                            f"They are currently in: **{actual_union_name}**", 
                            ephemeral=True
                        )
                    except:
                        await interaction.response.send_message(
                            f"❌ **{ign}** ({ign_type} IGN) is not in **{role.name}**", 
                            ephemeral=True
                        )
                else:
                    await interaction.response.send_message(
                        f"❌ **{ign}** ({ign_type} IGN) is not in any union", 
                        ephemeral=True
                    )
                return

            # Remove from the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = NULL WHERE discord_id = $1", row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = NULL WHERE discord_id = $1", row['discord_id'])

            # Get Discord user for display and role removal
            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to remove the role
                try:
                    member = interaction.guild.get_member(int(row['discord_id']))
                    if member:
                        # Check if user should still have this role (other IGN might still be in this union)
                        other_union = row['union_name_2'] if is_primary_ign else row['union_name']
                        if str(other_union) == str(role.id):
                            # Their other IGN is still in this union, don't remove role
                            role_status = " (Discord role kept - other IGN still in union)"
                        else:
                            # Remove the Discord role
                            await member.remove_roles(role, reason=f"Removed from union via admin command by {interaction.user}")
                            role_status = f" and removed **@{role.name}** Discord role"
                    else:
                        role_status = " (Discord role not removed - user not in server)"
                except Exception as role_error:
                    role_status = f" (Discord role removal failed: {str(role_error)})"
                    
            except:
                user_display = f"User ID: {row['discord_id']}"
                role_status = " (Discord role not removed - user not found)"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) removed from union **{role.name}** ({ign_type} IGN slot){role_status} (Admin override)", 
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionMembership(bot))

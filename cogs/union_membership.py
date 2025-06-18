import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class UnionMembership(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_admin_role(self, member):
        """Check if member has admin or mod+ role"""
        admin_roles = ["admin", "mod+"]
        return any(role.name.lower() in admin_roles for role in member.roles)

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

    @app_commands.command(name="add_user_to_union", description="Add user to YOUR union by IGN (auto-detects your union, transfers if already in another)")
    @app_commands.describe(ign="In-game name of the user to add", visible="Make this message visible to everyone (default: False)")
    async def add_user_to_union(self, interaction: discord.Interaction, ign: str, visible: bool = False):
        led_union_id = await self.get_user_led_union(interaction.user.id)
        if not led_union_id:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=not visible)
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
                    ephemeral=not visible
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
                    ephemeral=not visible
                )
                return

            # Handle transfer from previous union
            transfer_message = ""
            old_role_to_remove = None
            if current_union:
                try:
                    old_role_id = int(current_union)
                    old_role = interaction.guild.get_role(old_role_id)
                    old_union_name = old_role.name if old_role else f"Role ID: {old_role_id}"
                    transfer_message = f" (transferred from **{old_union_name}**)"
                    old_role_to_remove = old_role
                except:
                    old_union_name = current_union
                    transfer_message = f" (transferred from **{old_union_name}**)"

            # Update the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = $1 WHERE discord_id = $2", str(led_union_id), row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = $1 WHERE discord_id = $2", str(led_union_id), row['discord_id'])

            # Get Discord user for display and role assignment
            try:
                discord_user = await self.bot.fetch_user(int(row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to manage roles
                try:
                    member = interaction.guild.get_member(int(row['discord_id']))
                    if member:
                        role_changes = []
                        
                        # Remove old role if transferring and user shouldn't keep it
                        if old_role_to_remove:
                            # Check if their other IGN is still in the old union
                            other_union = row['union_name_2'] if is_primary_ign else row['union_name']
                            if str(other_union) != str(old_role_to_remove.id):
                                # Other IGN is not in old union, safe to remove role
                                await member.remove_roles(old_role_to_remove, reason=f"Transferred from union via leader command by {interaction.user}")
                                role_changes.append(f"removed **@{old_role_to_remove.name}**")
                        
                        # Assign the new Discord role
                        await member.add_roles(led_union_role, reason=f"Added to union via leader command by {interaction.user}")
                        role_changes.append(f"assigned **@{led_union_name}**")
                        
                        role_status = f" and {' and '.join(role_changes)} Discord role{'s' if len(role_changes) > 1 else ''}"
                    else:
                        role_status = " (Discord roles not changed - user not in server)"
                except Exception as role_error:
                    role_status = f" (Discord role management failed: {str(role_error)})"
                    
            except:
                user_display = f"User ID: {row['discord_id']}"
                role_status = " (Discord roles not changed - user not found)"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) added to your union **{led_union_name}** using {ign_type} IGN{transfer_message}{role_status}", 
                ephemeral=not visible
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error adding user to union: {str(e)}", ephemeral=not visible)
        finally:
            await conn.close()

    @app_commands.command(name="remove_user_from_union", description="Remove user from YOUR union by IGN")
    @app_commands.describe(ign="In-game name of the user to remove", visible="Make this message visible to everyone (default: False)")
    async def remove_user_from_union(self, interaction: discord.Interaction, ign: str, visible: bool = False):
        led_union_id = await self.get_user_led_union(interaction.user.id)
        if not led_union_id:
            await interaction.response.send_message("❌ You are not assigned as a union leader.", ephemeral=not visible)
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
                    ephemeral=not visible
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
                    ephemeral=not visible
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
                ephemeral=not visible
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing user from union: {str(e)}", ephemeral=not visible)
        finally:
            await conn.close()

    @app_commands.command(name="admin_add_user_to_union", description="Add user to ANY union by IGN (Admin override, auto-transfers)")
    @app_commands.describe(ign="In-game name of the user to add", role="Union role to add them to", visible="Make this message visible to everyone (default: False)")
    async def admin_add_user_to_union(self, interaction: discord.Interaction, ign: str, role: discord.Role, visible: bool = False):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin or @Mod+ role.", ephemeral=not visible)
            return

        conn = await get_connection()
        try:
            # Check if role is registered as union
            role_check = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if not role_check:
                await interaction.response.send_message(f"❌ Role **{role.name}** is not registered as union", ephemeral=not visible)
                return

            # Find user by IGN (primary or secondary)
            user_row = await conn.fetchrow(
                "SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE ign_primary = $1 OR ign_secondary = $1", 
                ign
            )
            
            if not user_row:
                await interaction.response.send_message(
                    f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first using `/register_primary_ign` or `/register_secondary_ign`.", 
                    ephemeral=not visible
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
                    ephemeral=not visible
                )
                return

            # Handle transfer from previous union
            transfer_message = ""
            old_role_to_remove = None
            if current_union:
                try:
                    old_role_id = int(current_union)
                    old_role = interaction.guild.get_role(old_role_id)
                    old_union_name = old_role.name if old_role else f"Role ID: {current_union}"
                    transfer_message = f" (transferred from **{old_union_name}**)"
                    old_role_to_remove = old_role
                except:
                    old_union_name = current_union
                    transfer_message = f" (transferred from **{old_union_name}**)"

            # Update the appropriate union slot
            if is_primary_ign:
                await conn.execute("UPDATE users SET union_name = $1 WHERE discord_id = $2", str(role.id), user_row['discord_id'])
            else:
                await conn.execute("UPDATE users SET union_name_2 = $1 WHERE discord_id = $2", str(role.id), user_row['discord_id'])

            # Get Discord user for display and role assignment
            try:
                discord_user = await self.bot.fetch_user(int(user_row['discord_id']))
                user_display = f"{discord_user.mention} ({discord_user.name})"
                
                # Try to get the member object to manage roles
                try:
                    member = interaction.guild.get_member(int(user_row['discord_id']))
                    if member:
                        role_changes = []
                        
                        # Remove old role if transferring and user shouldn't keep it
                        if old_role_to_remove:
                            # Check if their other IGN is still in the old union
                            other_union = user_row['union_name_2'] if is_primary_ign else user_row['union_name']
                            if str(other_union) != str(old_role_to_remove.id):
                                # Other IGN is not in old union, safe to remove role
                                await member.remove_roles(old_role_to_remove, reason=f"Transferred from union via admin command by {interaction.user}")
                                role_changes.append(f"removed **@{old_role_to_remove.name}**")
                        
                        # Assign the new Discord role
                        await member.add_roles(role, reason=f"Added to union via admin command by {interaction.user}")

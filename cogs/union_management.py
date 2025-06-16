import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class UnionManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def has_admin_role(self, member):
        """Check if member has admin or mod+ role"""
        admin_roles = ["admin", "mod+"]
        return any(role.name.lower() in admin_roles for role in member.roles)

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
            await interaction.response.send_message("❌ This command requires the @Admin or @Mod+ role.", ephemeral=True)
            return

        if not role.name.startswith("Union-"):
            await interaction.response.send_message("❌ Role name must start with 'Union-' prefix.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            # Check if already exists first
            existing = await conn.fetchrow("SELECT role_id FROM union_roles WHERE role_id = $1", role.id)
            if existing:
                await interaction.response.send_message(f"❌ Role **{role.name}** is already registered as union", ephemeral=True)
                return
            
            # Insert new union role
            await conn.execute("INSERT INTO union_roles (role_id) VALUES ($1)", role.id)
            await interaction.response.send_message(f"✅ Role **{role.name}** registered as union", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering union role: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_role_as_union", description="Deregister a union role (Admin only)")
    @app_commands.describe(role="Discord role to deregister")
    async def deregister_role_as_union(self, interaction: discord.Interaction, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin or @Mod+ role.", ephemeral=True)
            return

        conn = await get_connection()
        try:
            await conn.execute("DELETE FROM union_roles WHERE role_id = $1", role.id)
            await conn.execute("DELETE FROM union_leaders WHERE role_id = $1 OR role_id_2 = $1", role.id)
            await conn.execute("UPDATE users SET union_name = NULL WHERE union_name = $1", str(role.id))
            await conn.execute("UPDATE users SET union_name_2 = NULL WHERE union_name_2 = $1", str(role.id))
            await interaction.response.send_message(f"✅ Union **{role.name}** deregistered and all members removed", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error deregistering union role: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="appoint_union_leader", description="Appoint a union leader by IGN (Admin only)")
    @app_commands.describe(ign="In-game name of the player to appoint as leader", role="Union role")
    async def appoint_union_leader(self, interaction: discord.Interaction, ign: str, role: discord.Role):
        if not self.has_admin_role(interaction.user):
            await interaction.response.send_message("❌ This command requires the @Admin or @Mod+ role.", ephemeral=True)
            return

        # Find Discord user by IGN
        discord_id = await self.find_user_by_ign(ign)
        if not discord_id:
            await interaction.response.send_message(
                f"❌ No Discord user found with IGN **{ign}**. They must register their IGN first using `/register_primary_ign` or `/register_secondary_ign`.", 
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

            # Check current leadership status
            existing_leadership = await conn.fetchrow("SELECT role_id, role_id_2 FROM union_leaders WHERE user_id = $1", int(discord_id))
            
            # Determine which IGN slot this IGN belongs to
            user_data = await conn.fetchrow(
                "SELECT ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE discord_id = $1",
                discord_id
            )
            
            if not user_data:
                await interaction.response.send_message(
                    f"❌ User with IGN **{ign}** not found in database. They must register their IGN first.",
                    ephemeral=True
                )
                return
            
            is_primary_ign = (user_data['ign_primary'] == ign)
            is_secondary_ign = (user_data['ign_secondary'] == ign)
            
            if not is_primary_ign and not is_secondary_ign:
                await interaction.response.send_message(
                    f"❌ IGN **{ign}** is not registered for this Discord user.",
                    ephemeral=True
                )
                return
            
            ign_type = "Primary" if is_primary_ign else "Secondary"
            
            if existing_leadership:
                current_role_primary = existing_leadership['role_id']
                current_role_secondary = existing_leadership['role_id_2']
                
                # Check if this IGN is already leading another union
                if is_primary_ign and current_role_primary and current_role_primary != role.id:
                    # Primary IGN already leads another union
                    existing_role = interaction.guild.get_role(current_role_primary)
                    existing_role_name = existing_role.name if existing_role else f"Role ID: {current_role_primary}"
                    await interaction.response.send_message(
                        f"❌ **{ign}** (Primary IGN) is already leading **{existing_role_name}**. "
                        f"Use `/dismiss_union_leader` first to transfer leadership.",
                        ephemeral=True
                    )
                    return
                elif is_secondary_ign and current_role_secondary and current_role_secondary != role.id:
                    # Secondary IGN already leads another union
                    existing_role = interaction.guild.get_role(current_role_secondary)
                    existing_role_name = existing_role.name if existing_role else f"Role ID: {current_role_secondary}"
                    await interaction.response.send_message(
                        f"❌ **{ign}** (Secondary IGN) is already leading **{existing_role_name}**. "
                        f"Use `/dismiss_union_leader` first to transfer leadership.",
                        ephemeral=True
                    )
                    return
                elif (is_primary_ign and current_role_primary == role.id) or (is_secondary_ign and current_role_secondary == role.id):
                    # Already leading this union with this IGN
                    await interaction.response.send_message(
                        f"❌ **{ign}** is already the leader of **{role.name}**",
                        ephemeral=True
                    )
                    return
                
                # Update existing leadership record
                if is_primary_ign:
                    await conn.execute("UPDATE union_leaders SET role_id = $1 WHERE user_id = $2", role.id, int(discord_id))
                else:
                    await conn.execute("UPDATE union_leaders SET role_id_2 = $1 WHERE user_id = $2", role.id, int(discord_id))
            else:
                # Create new leadership record
                if is_primary_ign:
                    await conn.execute("INSERT INTO union_leaders (user_id, role_id, role_id_2) VALUES ($1, $2, NULL)", int(discord_id), role.id)
                else:
                    await conn.execute("INSERT INTO union_leaders (user_id, role_id, role_id_2) VALUES ($1, NULL, $2)", int(discord_id), role.id)

            # Properly add them as a member using the correct IGN slot
            if is_primary_ign:
                # Primary IGN appointment - update union_name
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (discord_id) DO UPDATE SET 
                        union_name = EXCLUDED.union_name,
                        username = EXCLUDED.username
                """, discord_id, 
                     user_display.split('(')[0].strip() if '(' in user_display else f"User_{discord_id}",
                     user_data['ign_primary'], 
                     user_data['ign_secondary'], 
                     str(role.id),
                     user_data['union_name_2'])
            else:
                # Secondary IGN appointment - update union_name_2
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (discord_id) DO UPDATE SET 
                        union_name_2 = EXCLUDED.union_name_2,
                        username = EXCLUDED.username
                """, discord_id, 
                     user_display.split('(')[0].strip() if '(' in user_display else f"User_{discord_id}",
                     user_data['ign_primary'], 
                     user_data['ign_secondary'], 
                     user_data['union_name'],
                     str(role.id))

            # Also assign the Discord role
            try:
                member = interaction.guild.get_member(int(discord_id))
                if member:
                    await member.add_roles(role, reason=f"Appointed as union leader by {interaction.user}")
                    role_status = f" and assigned **@{role.name}** Discord role"
                else:
                    role_status = " (Discord role not assigned - user not in server)"
            except Exception as role_error:
                role_status = f" (Discord role assignment failed: {str(role_error)})"

            await interaction.response.send_message(
                f"✅ **{ign}** ({user_display}) appointed as leader of **{role.name}** and automatically added as a member using {ign_type} IGN{role_status}", 
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
            await interaction.response.send_message("❌ This command requires the @Admin or @Mod+ role.", ephemeral=True)
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
            # Check current leadership status
            current_leadership = await conn.fetchrow("SELECT role_id, role_id_2 FROM union_leaders WHERE user_id = $1", int(discord_id))
            
            if not current_leadership:
                await interaction.response.send_message(f"❌ No leadership found for IGN **{ign}**", ephemeral=True)
                return
            
            # Determine which IGN slot this IGN belongs to
            user_data = await conn.fetchrow(
                "SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1",
                discord_id
            )
            
            if not user_data:
                await interaction.response.send_message(f"❌ User data not found for IGN **{ign}**", ephemeral=True)
                return
            
            is_primary_ign = (user_data['ign_primary'] == ign)
            is_secondary_ign = (user_data['ign_secondary'] == ign)
            
            if not is_primary_ign and not is_secondary_ign:
                await interaction.response.send_message(f"❌ IGN **{ign}** is not registered for this user", ephemeral=True)
                return
            
            # Check if this IGN is actually leading this role
            if is_primary_ign:
                if current_leadership['role_id'] != role.id:
                    await interaction.response.send_message(
                        f"❌ **{ign}** (Primary IGN) is not the leader of **{role.name}**", 
                        ephemeral=True
                    )
                    return
                # Remove primary leadership
                await conn.execute("UPDATE union_leaders SET role_id = NULL WHERE user_id = $1", int(discord_id))
            else:
                if current_leadership['role_id_2'] != role.id:
                    await interaction.response.send_message(
                        f"❌ **{ign}** (Secondary IGN) is not the leader of **{role.name}**", 
                        ephemeral=True
                    )
                    return
                # Remove secondary leadership - FIXED: was using $2 instead of $1
                await conn.execute("UPDATE union_leaders SET role_id_2 = NULL WHERE user_id = $1", int(discord_id))
            
            # Clean up record if both leadership slots are now NULL
            updated_leadership = await conn.fetchrow("SELECT role_id, role_id_2 FROM union_leaders WHERE user_id = $1", int(discord_id))
            if updated_leadership and not updated_leadership['role_id'] and not updated_leadership['role_id_2']:
                await conn.execute("DELETE FROM union_leaders WHERE user_id = $1", int(discord_id))
            
            # Get user display for response
            try:
                discord_user = await self.bot.fetch_user(int(discord_id))
                user_display = f"{discord_user.mention} ({discord_user.name})"
            except:
                user_display = f"User ID: {discord_id}"
            
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

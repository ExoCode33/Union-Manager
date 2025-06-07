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

            # Check if this specific IGN is already leading another union
            # First, determine which IGN slot this IGN belongs to for this user
            user_data = await conn.fetchrow(
                "SELECT ign_primary, ign_secondary, union_name, union_name_2 FROM users WHERE discord_id = $1",
                discord_id
            )
            
            if user_data:
                is_primary_ign = (user_data['ign_primary'] == ign)
                current_union_for_ign = user_data['union_name'] if is_primary_ign else user_data['union_name_2']
                ign_type = "Primary" if is_primary_ign else "Secondary"
                
                # Check if this IGN is already leading a union (by checking if user leads the union they're in with this IGN)
                if current_union_for_ign:
                    # Check if user is leader of the union this IGN is in
                    existing_leadership = await conn.fetchrow(
                        "SELECT role_id FROM union_leaders WHERE user_id = $1 AND role_id = $2", 
                        int(discord_id), int(current_union_for_ign)
                    )
                    
                    if existing_leadership and int(current_union_for_ign) != role.id:
                        # This IGN is already leading a different union
                        existing_role = interaction.guild.get_role(int(current_union_for_ign))
                        existing_role_name = existing_role.name if existing_role else f"Role ID: {current_union_for_ign}"
                        
                        await interaction.response.send_message(
                            f"❌ **{ign}** ({ign_type} IGN) is already leading **{existing_role_name}**. "
                            f"An IGN can only lead one union at a time. Use `/dismiss_union_leader` first if you want to transfer leadership.",
                            ephemeral=True
                        )
                        return
                    elif existing_leadership and int(current_union_for_ign) == role.id:
                        # This IGN is already leading this same union
                        await interaction.response.send_message(
                            f"❌ **{ign}** ({ign_type} IGN) is already the leader of **{role.name}**",
                            ephemeral=True
                        )
                        return

            # Check if role already has a leader and replace them
            existing_leader = await conn.fetchrow("SELECT user_id FROM union_leaders WHERE role_id = $1", role.id)
            
            if existing_leader:
                # Update existing leader
                await conn.execute("UPDATE union_leaders SET user_id = $1 WHERE role_id = $2", int(discord_id), role.id)
            else:
                # Insert new leader
                await conn.execute("INSERT INTO union_leaders (role_id, user_id) VALUES ($1, $2)", role.id, int(discord_id))

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
            current_leader = await conn.fetchrow("SELECT user_id FROM union_leaders WHERE role_id = $1", role.id)
            
            if not current_leader:
                await interaction.response.send_message(f"❌ No leader found for **{role.name}**", ephemeral=True)
                return
                
            if current_leader['user_id'] != int(discord_id):
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
            await conn.execute("DELETE FROM union_leaders WHERE role_id = $1 AND user_id = $2", role.id, int(discord_id))
            
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

import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return sqlite3.connect("database.db")

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT ul.role_name, ul.leader_id 
                FROM union_leaders ul
                JOIN union_roles ur ON ul.role_name = ur.role_name
                ORDER BY ul.role_name
            """)
            leaders = cursor.fetchall()
            
            if not leaders:
                await interaction.response.send_message("❌ No union leaders found.")
                return

            embed = discord.Embed(title="👑 Union Leaders", color=0x00ff00)
            
            for union_name, leader_id in leaders:
                try:
                    leader = await self.bot.fetch_user(int(leader_id))
                    leader_display = f"{leader.mention} ({leader.name})"
                except:
                    leader_display = f"Unknown User (ID: {leader_id})"
                
                embed.add_field(
                    name=f"**{union_name}**",
                    value=leader_display,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error retrieving union leaders: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="show_union_detail", description="Show all unions with member lists and crown emojis")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get all registered unions
            cursor.execute("SELECT role_name FROM union_roles ORDER BY role_name")
            unions = cursor.fetchall()
            
            if not unions:
                await interaction.response.send_message("❌ No unions found.")
                return

            embed = discord.Embed(title="🏛️ Union Details", color=0x0099ff)
            
            for (union_name,) in unions:
                # Get union leader
                cursor.execute("SELECT leader_id FROM union_leaders WHERE role_name = ?", (union_name,))
                leader_result = cursor.fetchone()
                leader_id = leader_result[0] if leader_result else None
                
                # Get all members of this union
                cursor.execute("""
                    SELECT discord_id, ign_primary, ign_secondary 
                    FROM users 
                    WHERE union_name = ? 
                    ORDER BY discord_id
                """, (union_name,))
                members = cursor.fetchall()
                
                if not members:
                    member_list = "No members"
                else:
                    member_entries = []
                    for discord_id, ign_primary, ign_secondary in members:
                        try:
                            user = await self.bot.fetch_user(int(discord_id))
                            crown = "👑 " if leader_id and discord_id == leader_id else ""
                            
                            # Build IGN display
                            ign_parts = []
                            if ign_primary:
                                ign_parts.append(ign_primary)
                            if ign_secondary:
                                ign_parts.append(ign_secondary)
                            
                            ign_display = f" ({' | '.join(ign_parts)})" if ign_parts else ""
                            member_entries.append(f"{crown}{user.mention}{ign_display}")
                        except:
                            crown = "👑 " if leader_id and discord_id == leader_id else ""
                            
                            # Build IGN display
                            ign_parts = []
                            if ign_primary:
                                ign_parts.append(ign_primary)
                            if ign_secondary:
                                ign_parts.append(ign_secondary)
                            
                            ign_display = f" ({' | '.join(ign_parts)})" if ign_parts else ""
                            member_entries.append(f"{crown}Unknown User (ID: {discord_id}){ign_display}")
                    
                    member_list = "\n".join(member_entries)
                
                embed.add_field(
                    name=f"**{union_name}**",
                    value=member_list,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error retrieving union details: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

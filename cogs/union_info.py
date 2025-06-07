import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_connection(self):
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ul.role_name, ul.leader_id, u.ign_primary, u.ign_secondary
                FROM union_leaders ul
                JOIN union_roles ur ON ul.role_name = ur.role_name
                LEFT JOIN users u ON ul.leader_id = u.discord_id
                ORDER BY ul.role_name
            """)
            rows = cursor.fetchall()

            if not rows:
                await interaction.response.send_message("❌ No union leaders found.")
                return

            embed = discord.Embed(title="👑 Union Leaders", color=0x00ff00)

            for row in rows:
                role_name = row["role_name"]
                leader_id = row["leader_id"]
                ign_primary = row["ign_primary"]
                ign_secondary = row["ign_secondary"]

                try:
                    leader = await self.bot.fetch_user(int(leader_id))
                    leader_display = f"{leader.mention} ({leader.name})"
                except:
                    leader_display = f"Unknown User (ID: {leader_id})"

                # Add IGN info if available
                ign_parts = []
                if ign_primary:
                    ign_parts.append(ign_primary)
                if ign_secondary:
                    ign_parts.append(ign_secondary)
                
                ign_display = f"\n**IGN:** {' | '.join(ign_parts)}" if ign_parts else ""

                embed.add_field(
                    name=f"**{role_name}**",
                    value=f"{leader_display}{ign_display}",
                    inline=False
                )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="show_union_detail", description="Show all unions with member lists and crown emojis")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT role_name FROM union_roles ORDER BY role_name")
            unions = cursor.fetchall()

            if not unions:
                await interaction.response.send_message("❌ No unions found.")
                return

            embed = discord.Embed(title="🏛️ Union Details", color=0x0099ff)

            for union_row in unions:
                role_name = union_row['role_name']

                # Get union leader
                cursor.execute("SELECT leader_id FROM union_leaders WHERE role_name = ?", (role_name,))
                leader_row = cursor.fetchone()
                leader_id = leader_row['leader_id'] if leader_row else None

                # Get all members
                cursor.execute("""
                    SELECT discord_id, ign_primary, ign_secondary
                    FROM users
                    WHERE union_name = ?
                    ORDER BY discord_id
                """, (role_name,))
                members = cursor.fetchall()

                if not members:
                    member_list = "No members"
                else:
                    member_entries = []
                    for record in members:
                        discord_id = record['discord_id']
                        ign_primary = record['ign_primary']
                        ign_secondary = record['ign_secondary']

                        try:
                            user = await self.bot.fetch_user(int(discord_id))
                            user_display = user.mention
                        except:
                            user_display = f"Unknown User (ID: {discord_id})"

                        # Add crown if this user is the leader
                        crown = "👑 " if leader_id and str(discord_id) == str(leader_id) else ""

                        # Format IGNs
                        ign_parts = []
                        if ign_primary:
                            ign_parts.append(ign_primary)
                        if ign_secondary:
                            ign_parts.append(ign_secondary)

                        ign_display = f" ({' | '.join(ign_parts)})" if ign_parts else ""
                        member_entries.append(f"{crown}{user_display}{ign_display}")

                    member_list = "\n".join(member_entries)

                embed.add_field(name=f"**{role_name}**", value=member_list, inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

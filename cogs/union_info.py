import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # Make sure this exists and uses asyncpg

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("""
                SELECT ul.role_name, ul.leader_id 
                FROM union_leaders ul
                JOIN union_roles ur ON ul.role_name = ur.role_name
                ORDER BY ul.role_name
            """)

            if not rows:
                await interaction.response.send_message("❌ No union leaders found.")
                return

            embed = discord.Embed(title="👑 Union Leaders", color=0x00ff00)

            for union_name, leader_id in rows:
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
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="show_union_detail", description="Show all unions with member lists and crown emojis")
    async def show_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_name FROM union_roles ORDER BY role_name")

            if not unions:
                await interaction.response.send_message("❌ No unions found.")
                return

            embed = discord.Embed(title="🏛️ Union Details", color=0x0099ff)

            for row in unions:
                union_name = row['role_name']

                leader_row = await conn.fetchrow(
                    "SELECT leader_id FROM union_leaders WHERE role_name = $1", union_name
                )
                leader_id = leader_row['leader_id'] if leader_row else None

                members = await conn.fetch(
                    """
                    SELECT discord_id, ign_primary, ign_secondary
                    FROM users
                    WHERE union_name = $1
                    ORDER BY discord_id
                    """,
                    union_name
                )

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

                        crown = "👑 " if leader_id and str(discord_id) == str(leader_id) else ""

                        ign_parts = []
                        if ign_primary:
                            ign_parts.append(ign_primary)
                        if ign_secondary:
                            ign_parts.append(ign_secondary)

                        ign_display = f" ({' | '.join(ign_parts)})" if ign_parts else ""
                        member_entries.append(f"{crown}{user_display}{ign_display}")

                    member_list = "\n".join(member_entries)

                embed.add_field(name=f"**{union_name}**", value=member_list, inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

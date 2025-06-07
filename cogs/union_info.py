import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # Uses asyncpg

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("""
                SELECT ul.role_id, ul.user_id
                FROM union_leaders ul
                JOIN union_roles ur ON ul.role_id = ur.role_id
                ORDER BY ul.role_id
            """)

            if not rows:
                await interaction.response.send_message("❌ No union leaders found.")
                return

            embed = discord.Embed(title="👑 Union Leaders", color=0x00ff00)

            for row in rows:
                role_id_str = str(row["role_id"])
                user_id = row["user_id"]

                role = interaction.guild.get_role(int(role_id_str))
                role_name = role.name if role else f"(Role ID: {role_id_str})"

                try:
                    leader = await self.bot.fetch_user(int(user_id))
                    leader_display = f"{leader.mention} ({leader.name})"
                except:
                    leader_display = f"Unknown User (ID: {user_id})"

                embed.add_field(
                    name=f"**{role_name}**",
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
            unions = await conn.fetch("SELECT role_id FROM union_roles ORDER BY role_id")

            if not unions:
                await interaction.response.send_message("❌ No unions found.")
                return

            embed = discord.Embed(title="🏛️ Union Details", color=0x0099ff)

            for row in unions:
                role_id_str = str(row['role_id'])       # for SQL
                role_id_int = int(row['role_id'])       # for Discord
                role = interaction.guild.get_role(role_id_int)
                role_name = role.name if role else f"(Role ID: {role_id_str})"

                leader_row = await conn.fetchrow(
                    "SELECT user_id FROM union_leaders WHERE role_id = $1", role_id_str
                )
                leader_id = leader_row['user_id'] if leader_row else None

                members = await conn.fetch(
                    """
                    SELECT discord_id, ign_primary, ign_secondary
                    FROM users
                    WHERE union_name = $1
                    ORDER BY discord_id
                    """,
                    role_id_str
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

                embed.add_field(name=f"**{role_name}**", value=member_list, inline=False)

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("""
                SELECT ul.role_id, ul.user_id, u.ign_primary, u.ign_secondary
                FROM union_leaders ul
                JOIN union_roles ur ON ul.role_id = ur.role_id
                LEFT JOIN users u ON ul.user_id = u.discord_id
                ORDER BY ul.role_id
            """)

            if not rows:
                await interaction.response.send_message("❌ No union leaders found.")
                return

            embed = discord.Embed(
                title="👑 **UNION LEADERSHIP**", 
                description="*All appointed union leaders with their IGN information*",
                color=0xFFD700
            )
            embed.set_footer(text="Use /appoint_union_leader to assign new leaders")

            for row in rows:
                role_id = int(row["role_id"])
                leader_id = row["user_id"]
                ign_primary = row["ign_primary"]
                ign_secondary = row["ign_secondary"]

                # Get the Discord role
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Unknown Role (ID: {role_id})"

                try:
                    leader = await self.bot.fetch_user(int(leader_id))
                    leader_display = f"**{leader.display_name}** ({leader.name})\n"
                    leader_display += f"🆔 `{leader.id}`"
                except:
                    leader_display = f"**Unknown User**\n🆔 `{leader_id}`"

                # Add IGN info if available with clear labels
                ign_parts = []
                if ign_primary:
                    ign_parts.append(f"🎮 **IGN:** {ign_primary}")
                if ign_secondary:
                    ign_parts.append(f"🎯 **Alt IGN:** {ign_secondary}")
                
                if ign_parts:
                    ign_display = f"\n{chr(10).join(ign_parts)}"
                else:
                    ign_display = f"\n⚠️ *No IGN registered*"

                embed.add_field(
                    name=f"🏛️ **{role_name}**",
                    value=f"{leader_display}{ign_display}\n\u200b",
                    inline=False
                )

            # Add summary
            total_leaders = len(rows)
            embed.add_field(
                name="📊 **SUMMARY**",
                value=f"**Total Leaders:** {total_leaders}",
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

            embed = discord.Embed(
                title="🏛️ **UNION OVERVIEW**", 
                description="*Complete list of all registered unions with their leaders and members*",
                color=0x2B2D31
            )
            embed.set_footer(text="👑 = Union Leader | Use /add_user_to_union to add members")

            for union_row in unions:
                role_id = int(union_row['role_id'])
                
                # Get the Discord role
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Unknown Role (ID: {role_id})"

                # Get union leader
                leader_row = await conn.fetchrow("SELECT user_id FROM union_leaders WHERE role_id = $1", role_id)
                leader_id = leader_row['user_id'] if leader_row else None

                # Get all members
                members = await conn.fetch("""
                    SELECT discord_id, ign_primary, ign_secondary
                    FROM users
                    WHERE union_name = $1
                    ORDER BY discord_id
                """, str(role_id))

                # Count total members
                member_count = len(members)
                
                # Check if leader exists but isn't in members table
                leader_in_members = False
                if leader_id:
                    leader_in_members = any(str(member['discord_id']) == str(leader_id) for member in members)
                    if not leader_in_members:
                        member_count += 1

                if member_count == 0:
                    if leader_id:
                        try:
                            leader_user = await self.bot.fetch_user(int(leader_id))
                            discord_name = leader_user.display_name
                            
                            leader_igns = await conn.fetchrow(
                                "SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1", 
                                leader_id
                            )
                            if leader_igns and (leader_igns['ign_primary'] or leader_igns['ign_secondary']):
                                ign_parts = []
                                if leader_igns['ign_primary']:
                                    ign_parts.append(leader_igns['ign_primary'])
                                if leader_igns['ign_secondary']:
                                    ign_parts.append(leader_igns['ign_secondary'])
                                
                                leader_display = f"**{discord_name}** ~ IGN: *{' | '.join(ign_parts)}*"
                            else:
                                leader_display = f"**{discord_name}** ~ IGN: *Not registered*"
                            
                            member_list = f"　👑 {leader_display}\n\n　　*No other members*"
                            member_count = 1
                        except:
                            member_list = f"　👑 **Unknown Leader**\n\n　　*No other members*"
                            member_count = 1
                    else:
                        member_list = "　🔍 **No leader assigned**\n　🔍 **No members**\n\n　　*Use `/appoint_union_leader` to assign a leader*"
                        member_count = 0
                else:
                    member_entries = []
                    leader_entry = None
                    
                    # Process all members
                    for record in members:
                        discord_id = record['discord_id']
                        ign_primary = record['ign_primary']
                        ign_secondary = record['ign_secondary']

                        try:
                            user = await self.bot.fetch_user(int(discord_id))
                            discord_name = user.display_name
                        except:
                            discord_name = f"Unknown User (ID: {discord_id})"

                        # Format IGNs
                        ign_parts = []
                        if ign_primary:
                            ign_parts.append(ign_primary)
                        if ign_secondary:
                            ign_parts.append(ign_secondary)

                        if ign_parts:
                            ign_display = ' | '.join(ign_parts)
                        else:
                            ign_display = "*Not registered*"

                        full_display = f"**{discord_name}** ~ IGN: *{ign_display}*"

                        # Check if this user is the leader
                        if leader_id and str(discord_id) == str(leader_id):
                            leader_entry = f"　👑 {full_display}"
                        else:
                            member_entries.append(f"　👤 {full_display}")
                    
                    # Handle leader not in members table
                    if leader_id and not leader_in_members:
                        try:
                            leader_user = await self.bot.fetch_user(int(leader_id))
                            discord_name = leader_user.display_name
                        except:
                            discord_name = f"Unknown User (ID: {leader_id})"
                        
                        leader_igns = await conn.fetchrow(
                            "SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1", 
                            leader_id
                        )
                        ign_parts = []
                        if leader_igns:
                            if leader_igns['ign_primary']:
                                ign_parts.append(leader_igns['ign_primary'])
                            if leader_igns['ign_secondary']:
                                ign_parts.append(leader_igns['ign_secondary'])
                        
                        ign_display = ' | '.join(ign_parts) if ign_parts else "*Not registered*"
                        leader_entry = f"　👑 **{discord_name}** ~ IGN: *{ign_display}*"

                    # Combine leader (always first) + members
                    all_entries = []
                    if leader_entry:
                        all_entries.append(leader_entry)
                    all_entries.extend(member_entries)
                    
                    member_list = "\n".join(all_entries)

                # Add field with member capacity
                embed.add_field(
                    name=f"# **{role_name}** ({member_count}/30 members)", 
                    value=f"{member_list}",
                    inline=False
                )

            # Add summary
            total_unions = len(unions)
            unions_with_leaders = await conn.fetchval("SELECT COUNT(*) FROM union_leaders")
            total_members = await conn.fetchval("SELECT COUNT(*) FROM users WHERE union_name IS NOT NULL")
            
            try:
                command_user = interaction.user
                user_data = await conn.fetchrow(
                    "SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1", 
                    str(command_user.id)
                )
                
                if user_data and (user_data['ign_primary'] or user_data['ign_secondary']):
                    user_ign = user_data['ign_primary'] or user_data['ign_secondary']
                    summary_example = f"**{command_user.display_name}** ~ IGN: *{user_ign}*"
                else:
                    summary_example = f"**{command_user.display_name}** ~ IGN: *Not registered*"
            except:
                summary_example = "**ExoCode** ~ IGN: *ExoCode#Test*"
            
            embed.add_field(
                name="📊 **SUMMARY**",
                value=f"**Total Unions:** {total_unions}\n**Unions with Leaders:** {unions_with_leaders}\n**Total Members:** {total_members}\n\n**Format Example:** {summary_example}",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

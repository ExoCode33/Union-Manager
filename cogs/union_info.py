import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    async def show_union_leader(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer()
        
        conn = await get_connection()
        try:
            rows = await conn.fetch("""
                SELECT ul.user_id, ul.role_id, ul.role_id_2, u.ign_primary, u.ign_secondary
                FROM union_leaders ul
                LEFT JOIN users u ON ul.user_id::text = u.discord_id
                WHERE ul.role_id IS NOT NULL OR ul.role_id_2 IS NOT NULL
                ORDER BY ul.user_id
            """)

            if not rows:
                await interaction.followup.send("❌ No union leaders found.")
                return

            embed = discord.Embed(
                title="👑 **UNION LEADERSHIP**", 
                description="*All appointed union leaders with their IGN information*",
                color=0xFFD700
            )
            embed.set_footer(text="Use /appoint_union_leader to assign new leaders")

            for row in rows:
                leader_id = row["user_id"]
                role_id_primary = row["role_id"]
                role_id_secondary = row["role_id_2"]
                ign_primary = row["ign_primary"]
                ign_secondary = row["ign_secondary"]

                try:
                    leader = await self.bot.fetch_user(int(leader_id))
                    leader_display = f"**{leader.display_name}** ({leader.name})\n"
                    leader_display += f"🆔 `{leader.id}`"
                except:
                    leader_display = f"**Unknown User**\n🆔 `{leader_id}`"

                # Show leadership for each role they lead
                leadership_info = []
                
                if role_id_primary:
                    role = interaction.guild.get_role(role_id_primary)
                    role_name = role.name if role else f"Role ID: {role_id_primary}"
                    primary_ign_display = f"🎮 **Primary IGN:** {ign_primary}" if ign_primary else "🎮 **Primary IGN:** *Not registered*"
                    leadership_info.append(f"🏛️ **{role_name}**\n{leader_display}\n{primary_ign_display}")
                
                if role_id_secondary:
                    role = interaction.guild.get_role(role_id_secondary)
                    role_name = role.name if role else f"Role ID: {role_id_secondary}"
                    secondary_ign_display = f"🎯 **Secondary IGN:** {ign_secondary}" if ign_secondary else "🎯 **Secondary IGN:** *Not registered*"
                    leadership_info.append(f"🏛️ **{role_name}**\n{leader_display}\n{secondary_ign_display}")
                
                for info in leadership_info:
                    embed.add_field(
                        name="👑 **LEADERSHIP**",
                        value=f"{info}\n\u200b",
                        inline=False
                    )

            # Add summary
            total_leaders = len(rows)
            embed.add_field(
                name="📊 **SUMMARY**",
                value=f"**Total Leaders:** {total_leaders}",
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="show_union_detail", description="Show all unions with member lists - no truncation")
    async def show_union_detail(self, interaction: discord.Interaction):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer()
        
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_id FROM union_roles ORDER BY role_id")

            if not unions:
                await interaction.followup.send("❌ No unions found.")
                return

            # Split into multiple messages if needed to avoid Discord limits
            messages = []
            current_message = ""
            
            for union_row in unions:
                role_id = int(union_row['role_id'])
                
                # Get the Discord role
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Unknown Role (ID: {role_id})"

                # Get union leader
                leader_row = await conn.fetchrow("SELECT user_id FROM union_leaders WHERE role_id = $1 OR role_id_2 = $1", role_id)
                leader_id = leader_row['user_id'] if leader_row else None

                # Get ALL members - no limit
                members = await conn.fetch("""
                    SELECT discord_id, ign_primary, ign_secondary, union_name, union_name_2
                    FROM users
                    WHERE union_name = $1 OR union_name_2 = $1
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

                union_text = f"\n# **{role_name}** ({member_count}/30 members)\n"

                if member_count == 0:
                    if leader_id:
                        try:
                            leader_user = await self.bot.fetch_user(int(leader_id))
                            discord_name = leader_user.display_name
                            
                            # Get leader IGN
                            leader_igns = await conn.fetchrow(
                                "SELECT ign_primary, ign_secondary FROM users WHERE discord_id = $1", 
                                str(leader_id)
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
                            
                            member_list = f"👑 {leader_display}\n\n*No other members*"
                        except:
                            member_list = f"👑 **Unknown Leader**\n\n*No other members*"
                    else:
                        member_list = "🔍 **No leader assigned**\n🔍 **No members**\n\n*Use `/appoint_union_leader` to assign a leader*"
                else:
                    member_entries = []
                    leader_entry = None
                    
                    # Process ALL members - no truncation
                    for record in members:
                        discord_id = record['discord_id']
                        ign_primary = record['ign_primary']
                        ign_secondary = record['ign_secondary']
                        union_name = record['union_name']
                        union_name_2 = record['union_name_2']

                        # Get Discord name
                        try:
                            member_obj = interaction.guild.get_member(int(discord_id))
                            if member_obj:
                                discord_name = member_obj.display_name
                            else:
                                user = await self.bot.fetch_user(int(discord_id))
                                discord_name = user.display_name
                        except:
                            discord_name = f"Unknown User (ID: {discord_id})"

                        # Determine which IGN to show based on which union slot matches
                        if str(union_name) == str(role_id):
                            relevant_ign = ign_primary if ign_primary else "*Not registered*"
                        elif str(union_name_2) == str(role_id):
                            relevant_ign = ign_secondary if ign_secondary else "*Not registered*"
                        else:
                            relevant_ign = "*Unknown*"

                        full_display = f"**{discord_name}** ~ IGN: *{relevant_ign}*"

                        # Check if this user is the leader
                        if leader_id and str(discord_id) == str(leader_id):
                            leader_entry = f"👑 {full_display}"
                        else:
                            member_entries.append(f"👤 {full_display}")
                    
                    # Handle leader not in members table
                    if leader_id and not leader_in_members:
                        try:
                            leader_user = await self.bot.fetch_user(int(leader_id))
                            discord_name = leader_user.display_name
                        except:
                            discord_name = f"Unknown User (ID: {leader_id})"
                        
                        leader_entry = f"👑 **{discord_name}** ~ IGN: *Not in union*"

                    # Combine leader (always first) + ALL members
                    all_entries = []
                    if leader_entry:
                        all_entries.append(leader_entry)
                    all_entries.extend(member_entries)  # NO TRUNCATION
                    
                    member_list = "\n".join(all_entries)

                union_text += member_list + "\n"
                
                # Check if adding this union would exceed Discord's message limit (2000 chars)
                if len(current_message + union_text) > 1900:  # Leave some buffer
                    if current_message:
                        messages.append(current_message)
                    current_message = union_text
                else:
                    current_message += union_text
            
            # Add any remaining content
            if current_message:
                messages.append(current_message)
            
            # Send all messages
            if not messages:
                await interaction.followup.send("❌ No union data found.")
                return
            
            # Send first message with title
            first_message = f"🏛️ **UNION OVERVIEW**\n*Complete list of all registered unions with their leaders and members*\n{messages[0]}"
            await interaction.followup.send(first_message)
            
            # Send additional messages if needed
            for i, message in enumerate(messages[1:], 2):
                await interaction.followup.send(f"🏛️ **UNION OVERVIEW (Part {i})**\n{message}")

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

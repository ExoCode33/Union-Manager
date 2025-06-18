# Send embeds
            if not embeds:
                await interaction.followup.send("❌ No union data found.", ephemeral=not visible)
                return
            
            # Send first embed with appropriate message
            if union_name:
                await interaction.followup.send(f"🔍 **Union Search Result for '{union_name}'**", embed=embeds[0], ephemeral=not visible)
            else:
                members_text = " (members hidden)" if not show_members else ""
                await interaction.followup.send(f"🏛️ **Union Overview** ({len(embeds)} unions){members_text}", embed=embeds[0], ephemeral=not visible)
            
            # Send additional embeds if showing all unions
            for i, embed in enumerate(embeds[1:], 2):
                members_text = " (members hidden)" if not show_members else ""
                await interaction.followup.send(f"🏛️ **Union Overview (Part {i})**{members_text}", embed=embed, ephemeral=not visible)import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.db import get_connection

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auto_cleanup.start()  # Start the automated cleanup task

    def cog_unload(self):
        self.auto_cleanup.cancel()  # Stop the task when cog is unloaded

    def has_admin_role(self, member):
        """Check if member has admin or mod+ role"""
        admin_roles = ["admin", "mod+"]
        return any(role.name.lower() in admin_roles for role in member.roles)

    @tasks.loop(hours=12)
    async def auto_cleanup(self):
        """Automated cleanup task that runs every 12 hours"""
        try:
            # Find the union-leader channel in all guilds
            target_channel = None
            for guild in self.bot.guilds:
                for channel in guild.text_channels:
                    if channel.name.lower() == "union-leader":
                        target_channel = channel
                        break
                if target_channel:
                    break
            
            if not target_channel:
                print("⚠️ Auto-cleanup: No 'union-leader' channel found")
                return
            
            guild = target_channel.guild
            conn = await get_connection()
            
            try:
                # Get all users from database
                all_users = await conn.fetch("SELECT discord_id, username, ign_primary, ign_secondary, union_name, union_name_2 FROM users ORDER BY discord_id")
                
                if not all_users:
                    return  # No users to check
                
                # Track statistics and affected leaders
                total_users = len(all_users)
                users_still_in_guild = 0
                users_left_guild = 0
                leaders_affected = 0
                cleanup_actions = []
                affected_leaders = set()  # Track unique affected leaders
                
                # Check each user
                for user_record in all_users:
                    discord_id = user_record['discord_id']
                    username = user_record['username']
                    ign_primary = user_record['ign_primary']
                    ign_secondary = user_record['ign_secondary']
                    union_name = user_record['union_name']
                    union_name_2 = user_record['union_name_2']
                    
                    # Check if user is still in the guild
                    member = guild.get_member(int(discord_id))
                    
                    if member:
                        # User is still in guild
                        users_still_in_guild += 1
                    else:
                        # User has left the guild - needs cleanup
                        users_left_guild += 1
                        
                        # Check if this user was a union leader
                        leader_check = await conn.fetchrow("SELECT role_id, role_id_2 FROM union_leaders WHERE user_id = $1", int(discord_id))
                        was_leader = leader_check is not None
                        if leader_check:
                            leaders_affected += 1
                            
                            # Remove from leadership
                            await conn.execute("DELETE FROM union_leaders WHERE user_id = $1", int(discord_id))
                            
                            # Get role names for logging
                            role_names = []
                            if leader_check['role_id']:
                                role = guild.get_role(leader_check['role_id'])
                                role_names.append(role.name if role else f"Role ID: {leader_check['role_id']}")
                            if leader_check['role_id_2']:
                                role = guild.get_role(leader_check['role_id_2'])
                                role_names.append(role.name if role else f"Role ID: {leader_check['role_id_2']}")
                            
                            cleanup_actions.append(f"👑 **Leader removed:** {username} from {' & '.join(role_names)}")
                        
                        # Check which unions this user was a member of and find their leaders
                        member_unions = []
                        if union_name:
                            member_unions.append(union_name)
                        if union_name_2:
                            member_unions.append(union_name_2)
                        
                        # Find leaders of unions this member was part of
                        for union_id in member_unions:
                            try:
                                union_leaders = await conn.fetch(
                                    "SELECT user_id FROM union_leaders WHERE role_id = $1 OR role_id_2 = $1", 
                                    int(union_id)
                                )
                                for leader_record in union_leaders:
                                    leader_id = leader_record['user_id']
                                    # Only add if the leader is still in the guild and not the user who left
                                    if leader_id != int(discord_id):
                                        leader_member = guild.get_member(leader_id)
                                        if leader_member:
                                            affected_leaders.add(leader_id)
                            except:
                                pass  # Skip invalid union IDs
                        
                        # Log cleanup to history table before removing user
                        await conn.execute("""
                            INSERT INTO cleanup_history (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2, was_leader, cleanup_date, admin_id)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_DATE, $8)
                        """, discord_id, username, ign_primary, ign_secondary, union_name, union_name_2, was_leader, "AUTO_CLEANUP")
                        
                        # Remove user from database entirely
                        await conn.execute("DELETE FROM users WHERE discord_id = $1", discord_id)
                        
                        # Log the cleanup action
                        ign_display = []
                        if ign_primary:
                            ign_display.append(f"Primary: {ign_primary}")
                        if ign_secondary:
                            ign_display.append(f"Secondary: {ign_secondary}")
                        ign_text = f" ({' | '.join(ign_display)})" if ign_display else ""
                        
                        union_display = []
                        if union_name:
                            try:
                                role = guild.get_role(int(union_name)) if union_name.isdigit() else None
                                union_display.append(role.name if role else union_name)
                            except:
                                union_display.append(union_name)
                        if union_name_2:
                            try:
                                role = guild.get_role(int(union_name_2)) if union_name_2.isdigit() else None
                                union_display.append(role.name if role else union_name_2)
                            except:
                                union_display.append(union_name_2)
                        union_text = f" from {' & '.join(union_display)}" if union_display else ""
                        
                        cleanup_actions.append(f"👤 **User removed:** {username}{ign_text}{union_text}")
                
                # Only post if there were changes
                if users_left_guild > 0:
                    # Create summary embed
                    embed = discord.Embed(
                        title="🔄 **AUTOMATED DATABASE CLEANUP**",
                        description="*12-hour automated cleanup completed*",
                        color=0xFFA500
                    )
                    
                    # Add statistics
                    embed.add_field(
                        name="📊 **STATISTICS**",
                        value=f"**Total users checked:** {total_users}\n"
                              f"**Users still in Discord:** {users_still_in_guild}\n"
                              f"**Users who left Discord:** {users_left_guild}\n"
                              f"**Leaders affected:** {leaders_affected}",
                        inline=False
                    )
                    
                    # Add cleanup actions (limit to avoid embed size issues)
                    if cleanup_actions:
                        action_text = "\n".join(cleanup_actions[:10])  # Show first 10 actions
                        if len(cleanup_actions) > 10:
                            action_text += f"\n... and {len(cleanup_actions) - 10} more actions"
                        
                        embed.add_field(
                            name="🧹 **CLEANUP ACTIONS**",
                            value=action_text,
                            inline=False
                        )
                    
                    # Add recommendations
                    if leaders_affected > 0:
                        embed.add_field(
                            name="⚠️ **ATTENTION NEEDED**",
                            value=f"**{leaders_affected} union leader(s) were removed.** Use `/appoint_union_leader` to assign new leaders for affected unions.",
                            inline=False
                        )
                    
                    embed.set_footer(text="Automated cleanup runs every 12 hours • Use /show_cleanup_history for full details")
                    
                    # Create mention string for affected leaders
                    leader_mentions = []
                    for leader_id in affected_leaders:
                        leader_member = guild.get_member(leader_id)
                        if leader_member:
                            leader_mentions.append(leader_member.mention)
                    
                    # Send message with leader pings if any
                    if leader_mentions:
                        ping_message = f"🔔 **Union Leaders:** {' '.join(leader_mentions[:10])}"  # Limit to 10 mentions
                        if len(leader_mentions) > 10:
                            ping_message += f" and {len(leader_mentions) - 10} others"
                        ping_message += "\n*Members from your unions have left Discord - please review the cleanup report below.*"
                        await target_channel.send(ping_message)
                    
                    await target_channel.send(embed=embed)
                    print(f"✅ Auto-cleanup completed: {users_left_guild} users removed, posted to #{target_channel.name}")
                    if affected_leaders:
                        print(f"📢 Pinged {len(affected_leaders)} union leaders about member departures")
                
                else:
                    print("✅ Auto-cleanup completed: No users needed removal")
                    
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ **AUTOMATED CLEANUP ERROR**",
                    description=f"*Error during automated cleanup: {str(e)}*",
                    color=0xFF0000
                )
                await target_channel.send(embed=error_embed)
                print(f"❌ Auto-cleanup error: {str(e)}")
            finally:
                await conn.close()
                
        except Exception as e:
            print(f"❌ Auto-cleanup task error: {str(e)}")

    @auto_cleanup.before_loop
    async def before_auto_cleanup(self):
        """Wait until the bot is ready before starting the cleanup loop"""
        await self.bot.wait_until_ready()
        print("🔄 Auto-cleanup task started - runs every 12 hours")

    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assignments")
    @app_commands.describe(visible="Make this message visible to everyone (default: True)")
    async def show_union_leader(self, interaction: discord.Interaction, visible: bool = True):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=not visible)
        
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
                await interaction.followup.send("❌ No union leaders found.", ephemeral=not visible)
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

            await interaction.followup.send(embed=embed, ephemeral=not visible)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="show_union_detail", description="Show all unions with member lists in embed format")
    @app_commands.describe(
        union_name="Optional: Specific union name to show (case insensitive)",
        show_members="Optional: Show member list (default: True)",
        visible="Make this message visible to everyone (default: True)"
    )
    async def show_union_detail(self, interaction: discord.Interaction, union_name: str = None, show_members: bool = True, visible: bool = True):
        # Defer the response immediately to prevent timeout
        await interaction.response.defer(ephemeral=not visible)
        
        conn = await get_connection()
        try:
            # If union_name is provided, search for specific union (case insensitive)
            if union_name:
                # Get all registered unions from database
                all_unions = await conn.fetch("SELECT role_id FROM union_roles ORDER BY role_id")
                
                # Find matching union by name (case insensitive) - only from registered unions
                matching_union = None
                available_unions = []
                
                for union_row in all_unions:
                    role_id = int(union_row['role_id'])
                    role = interaction.guild.get_role(role_id)
                    if role:
                        available_unions.append(role.name)  # Track available unions for error message
                        if union_name.lower() in role.name.lower():
                            matching_union = union_row
                            break
                
                if not matching_union:
                    union_list = "\n".join([f"• {name}" for name in available_unions[:10]])  # Show up to 10
                    if len(available_unions) > 10:
                        union_list += f"\n... and {len(available_unions) - 10} more"
                    
                    await interaction.followup.send(
                        f"❌ No registered union found matching **{union_name}**\n\n"
                        f"**Available registered unions:**\n{union_list}\n\n"
                        f"Use `/show_union_detail` without parameters to see all unions.",
                        ephemeral=not visible
                    )
                    return
                
                unions = [matching_union]  # Only process the matching union
            else:
                unions = await conn.fetch("SELECT role_id FROM union_roles ORDER BY role_id")

            if not unions:
                await interaction.followup.send("❌ No unions found.", ephemeral=not visible)
                return

            # Create embed(s) with member lists
            embeds = []
            
            for union_row in unions:
                role_id = int(union_row['role_id'])
                
                # Get the Discord role
                role = interaction.guild.get_role(role_id)
                role_name = role.name if role else f"Unknown Role (ID: {role_id})"

                # Get union leader
                leader_row = await conn.fetchrow("SELECT user_id FROM union_leaders WHERE role_id = $1 OR role_id_2 = $1", role_id)
                leader_id = leader_row['user_id'] if leader_row else None

                # Get ALL members
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

                # Create embed for this union
                embed = discord.Embed(
                    title=f"🏛️ **{role_name}**", 
                    description=f"*Union Members ({member_count}/30)*",
                    color=0x7B68EE  # Purple color
                )

                # Only show members if show_members is True
                if show_members:
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
                        
                        embed.add_field(name="Members", value=member_list, inline=False)
                    else:
                        member_entries = []
                        leader_entry = None
                        
                        # Process members and create sortable list
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
                                leader_entry = {
                                    'display': f"👑 {full_display}",
                                    'sort_key': relevant_ign.lower() if relevant_ign != "*Not registered*" and relevant_ign != "*Unknown*" else "zzz"
                                }
                            else:
                                member_entries.append({
                                    'display': f"👤 {full_display}",
                                    'sort_key': relevant_ign.lower() if relevant_ign != "*Not registered*" and relevant_ign != "*Unknown*" else "zzz"
                                })
                        
                        # Handle leader not in members table
                        if leader_id and not leader_in_members:
                            try:
                                leader_user = await self.bot.fetch_user(int(leader_id))
                                discord_name = leader_user.display_name
                            except:
                                discord_name = f"Unknown User (ID: {leader_id})"
                            
                            leader_entry = {
                                'display': f"👑 **{discord_name}** ~ IGN: *Not in union*",
                                'sort_key': "zzz"  # Put at end since not in union
                            }

                        # Sort member entries alphabetically by IGN
                        member_entries.sort(key=lambda x: x['sort_key'])

                        # Combine leader + sorted members with character limit per field
                        all_entries = []
                        if leader_entry:
                            all_entries.append(leader_entry['display'])
                        
                        # Apply 35 line restriction (subtract 1 for leader if present)
                        max_members = 34 if leader_entry else 35
                        all_entries.extend([entry['display'] for entry in member_entries[:max_members]])
                        
                        # Add truncation notice if needed
                        if len(member_entries) > max_members:
                            remaining = len(member_entries) - max_members
                            all_entries.append(f"\n*... and {remaining} more members (35 line limit)*")
                        
                        # Try to fit everything in one field first
                        full_member_list = "\n".join(all_entries)
                        
                        if len(full_member_list) <= 1024:
                            # Fits in one field
                            embed.add_field(name="Members", value=full_member_list, inline=False)
                        else:
                            # Need to split, but minimize visible gaps
                            current_chunk = []
                            current_length = 0
                            field_count = 0
                            
                            for entry in all_entries:
                                entry_length = len(entry) + 1  # +1 for newline
                                
                                # If adding this entry would exceed limit, save current chunk
                                if current_length + entry_length > 1000 and current_chunk:
                                    field_count += 1
                                    if field_count == 1:
                                        embed.add_field(name="Members", value="\n".join(current_chunk), inline=False)
                                    else:
                                        # Use minimal spacing for continuation
                                        embed.add_field(name="\u200b", value="\n".join(current_chunk), inline=False)
                                    
                                    # Start new chunk
                                    current_chunk = [entry]
                                    current_length = entry_length
                                else:
                                    # Add to current chunk
                                    current_chunk.append(entry)
                                    current_length += entry_length
                            
                            # Add remaining entries
                            if current_chunk:
                                field_count += 1
                                if field_count == 1:
                                    embed.add_field(name="Members", value="\n".join(current_chunk), inline=False)
                                else:
                                    embed.add_field(name="\u200b", value="\n".join(current_chunk), inline=False)
                else:
                    # show_members is False - only show summary info
                    if leader_id:
                        try:
                            leader_user = await self.bot.fetch_user(int(leader_id))
                            leader_name = leader_user.display_name
                            leader_info = f"👑 **Leader:** {leader_name}"
                        except:
                            leader_info = f"👑 **Leader:** Unknown User (ID: {leader_id})"
                    else:
                        leader_info = "🔍 **No leader assigned**"
                    
                    embed.add_field(
                        name="Summary", 
                        value=f"{leader_info}\n👥 **Total Members:** {member_count}/30", 
                        inline=False
                    )

                embeds.append(embed)
            
            # Send embeds
            if not embeds:
                await interaction.followup.send("❌ No union data found.", ephemeral=ephemeral)
                return
            
            # Send first embed with appropriate message
            if union_name:
                await interaction.followup.send(f"🔍 **Union Search Result for '{union_name}'**", embed=embeds[0], ephemeral=ephemeral)
            else:
                members_text = " (members hidden)" if not show_members else ""
                await interaction.followup.send(f"🏛️ **Union Overview** ({len(embeds)} unions){members_text}", embed=embeds[0], ephemeral=ephemeral)
            
            # Send additional embeds if showing all unions
            for i, embed in enumerate(embeds[1:], 2):
                members_text = " (members hidden)" if not show_members else ""
                await interaction.followup.send(f"🏛️ **Union Overview (Part {i})**{members_text}", embed=embed, ephemeral=ephemeral)

        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionInfo(bot))

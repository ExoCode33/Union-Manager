import discord
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
                            action_text += f"\n... and {len(cleanup_actions) - 10} more actions

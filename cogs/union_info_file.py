import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # /show_union_leader
    @app_commands.command(name="show_union_leader", description="Show all union leaders and their assigned unions")
    async def show_union_leader(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            leaders = await conn.fetch("SELECT user_id, role_id FROM union_leaders ORDER BY role_id")
        finally:
            await conn.close()

        if not leaders:
            await interaction.response.send_message("👑 No union leaders found.")
            return

        lines = ["👑 **Union Leaders:**", ""]
        
        for leader in leaders:
            user_id = leader['user_id']
            role_id = leader['role_id']
            
            discord_member = guild.get_member(user_id)
            if discord_member:
                display_name = discord_member.display_name
                username = discord_member.name
                user_display = f"{display_name} ({username})"
            else:
                user_display = f"Unknown User (ID: {user_id})"
            
            role = guild.get_role(role_id)
            if role:
                role_name = role.name
            else:
                role_name = f"Unknown Role (ID: {role_id})"
            
            lines.append(f"• **{user_display}** → `{role_name}`")

        message = "\n".join(lines)
        await interaction.response.send_message(message)

    # /show_union_detail
    @app_commands.command(name="show_union_detail", description="Show all union roles with member lists")
    async def show_union_detail(self, interaction: discord.Interaction):
        guild = interaction.guild
        conn = await get_connection()
        try:
            unions = await conn.fetch("SELECT role_id FROM union_roles")
            members = await conn.fetch("SELECT union_role_id, username, user_id, ign FROM users WHERE union_role_id IS NOT NULL ORDER BY username")
            leaders = await conn.fetch("SELECT user_id, role_id FROM union_leaders")
        finally:
            await conn.close()

        if not unions:
            await interaction.response.send_message("📭 No unions found.")
            return

        # Create leader lookup map
        leader_map = {}
        for leader in leaders:
            role_id = str(leader['role_id'])
            if role_id not in leader_map:
                leader_map[role_id] = set()
            leader_map[role_id].add(leader['user_id'])

        # Group members by union role
        union_members = {}
        for member in members:
            role_id = member['union_role_id']
            if role_id not in union_members:
                union_members[role_id] = []
            union_members[role_id].append(member)

        lines = []
        for row in unions:
            rid = row['role_id']
            role = guild.get_role(rid)
            if role:
                role_members = union_members.get(str(rid), [])
                member_count = len(role_members)
                lines.append(f"**{role.name}** — {member_count}/30 members")
                
                if role_members:
                    for member in role_members:
                        discord_member = guild.get_member(member['user_id'])
                        display_name = discord_member.display_name if discord_member else member['username']
                        is_leader = str(rid) in leader_map and member['user_id'] in leader_map[str(rid)]
                        crown_emoji = " 👑" if is_leader else ""
                        ign = member['ign'] or "No IGN"
                        lines.append(f"  • **{display_name}**{crown_emoji} | IGN: `{ign}`")
                else:
                    lines.append("  • No members")
                lines.append("")

        if lines and lines[-1] == "":
            lines.pop()

        message = "\n".join(lines)
        await interaction.response.send_message(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(UnionInfo(bot))
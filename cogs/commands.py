import discord
from discord import app_commands
from discord.ext import commands
from utils.db import get_connection

class UnionCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_union(self, user_id):
        conn = await get_connection()
        try:
            row = await conn.fetchrow("SELECT union_name FROM users WHERE user_id = $1", str(user_id))
            return row["union_name"] if row else None
        finally:
            await conn.close()

    @app_commands.command(name="register_ign", description="Register your in-game name (IGN).")
    async def register_ign(self, interaction: discord.Interaction, ign: str):
        user = interaction.user
        user_union = await self.get_user_union(user.id)
        if not user_union:
            await interaction.response.send_message("❌ You must be assigned to a union before registering your IGN.")
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO users (user_id, discord_name, ign, union_name) VALUES ($1, $2, $3, $4) "
                "ON CONFLICT (user_id) DO UPDATE SET ign = EXCLUDED.ign",
                str(user.id), str(user), ign, user_union
            )
            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
        finally:
            await conn.close()

    @app_commands.command(name="add_to_union", description="Assign a user to your union.")
    async def add_to_union(self, interaction: discord.Interaction, member: discord.Member):
        leader = interaction.user
        leader_union = await self.get_user_union(leader.id)
        if not leader_union:
            await interaction.response.send_message("❌ You are not assigned to a union.")
            return

        conn = await get_connection()
        try:
            await conn.execute(
                "INSERT INTO users (user_id, discord_name, union_name) VALUES ($1, $2, $3) "
                "ON CONFLICT (user_id) DO UPDATE SET union_name = EXCLUDED.union_name",
                str(member.id), str(member), leader_union
            )
            await interaction.response.send_message(f"✅ {member.mention} has been added to the union `{leader_union}`.")
        finally:
            await conn.close()

    @app_commands.command(name="list_union_detail", description="List all registered union roles.")
    async def list_union_detail(self, interaction: discord.Interaction):
        conn = await get_connection()
        try:
            rows = await conn.fetch("SELECT role_id, union_name, leader_id FROM union_roles")
            if not rows:
                await interaction.response.send_message("ℹ️ No union roles registered.")
                return

            message = "📋 **Registered Union Roles:**
"
            for row in rows:
                role = interaction.guild.get_role(int(row["role_id"]))
                leader = interaction.guild.get_member(int(row["leader_id"])) if row["leader_id"] else None
                message += f"- {role.mention if role else 'Unknown Role'}: `{row['union_name']}`"
                if leader:
                    message += f" (Leader: {leader.mention})"
                message += "
"
            await interaction.response.send_message(message)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(UnionCommands(bot))

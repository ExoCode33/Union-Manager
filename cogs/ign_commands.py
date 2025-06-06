import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from utils.permissions import is_manager

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

class IGNCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(user="The Discord user", ign="Their in-game name")
    async def register_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("Permission denied.", ephemeral=True)
            return
        cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign) VALUES (?, ?)", (str(user.id), ign))
        conn.commit()
        await interaction.response.send_message(f"{user.mention}'s IGN registered as `{ign}`.")

async def setup(bot):
    await bot.add_cog(IGNCommands(bot))

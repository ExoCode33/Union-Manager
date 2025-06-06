import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from utils.permissions import is_manager

# ✅ Always use absolute path to DB (consistent with bot.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database.db")

class IGNCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(user="The Discord user", ign="Their in-game name")
    async def register_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign) VALUES (?, ?)", (str(user.id), ign))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ An error occurred while registering IGN.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(IGNCommands(bot))


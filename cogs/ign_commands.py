import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
from utils.permissions import is_manager

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
            # Safe DB connection per command
            conn = sqlite3.connect("database.db")
            cursor = conn.cursor()

            cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign) VALUES (?, ?)", (str(user.id), ign))
            conn.commit()
            conn.close()

            await interaction.response.send_message(f"✅ {user.mention}'s IGN has been registered as `{ign}`.")
        except Exception as e:
            await interaction.response.send_message("⚠️ An error occurred while registering IGN.", ephemeral=True)
            print(f"[DB ERROR] {e}")

async def setup(bot):
    await bot.add_cog(IGNCommands(bot))

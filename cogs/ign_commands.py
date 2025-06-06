import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
from utils.permissions import is_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "database.db")

class IGNCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Register IGN
    @app_commands.command(name="register_ign", description="Register a user's IGN")
    @app_commands.describe(user="The Discord user", ign="Their in-game name")
    async def register_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
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
            await interaction.response.send_message("⚠️ Failed to register IGN.", ephemeral=True)

    # Unregister IGN
    @app_commands.command(name="unregister_ign", description="Remove a user's IGN")
    @app_commands.describe(user="The user to remove")
    async def unregister_ign(self, interaction: discord.Interaction, user: discord.Member):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ign = '' WHERE discord_id = ?", (str(user.id),))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"🗑️ {user.mention}'s IGN has been removed.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to unregister IGN.", ephemeral=True)

    # Show user
    @app_commands.command(name="show_user", description="View a user's IGN and union")
    @app_commands.describe(user="The user to look up")
    async def show_user(self, interaction: discord.Interaction, user: discord.Member):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT ign, union_name FROM users WHERE discord_id = ?", (str(user.id),))
            result = cursor.fetchone()
            conn.close()
            if result:
                ign, union = result
                await interaction.response.send_message(f"📋 **{user.mention}**\n• IGN: `{ign}`\n• Union: `{union or 'None'}`")
            else:
                await interaction.response.send_message(f"❌ {user.mention} is not registered.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to show user.", ephemeral=True)

    # Register union role
    @app_commands.command(name="register_union_role", description="Register a union role")
    @app_commands.describe(role_name="The union role to register")
    async def register_union_role(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO union_roles (role_name) VALUES (?)", (role_name,))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"✅ Union role `{role_name}` registered.")
        except sqlite3.IntegrityError:
            await interaction.response.send_message(f"⚠️ Union role `{role_name}` is already registered.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to register union role.", ephemeral=True)

    # Deregister union role
    @app_commands.command(name="deregister_union_role", description="Remove a registered union role")
    @app_commands.describe(role_name="The union role to deregister")
    async def deregister_union_role(self, interaction: discord.Interaction, role_name: str):
        if not is_manager(interaction.user):
            await interaction.response.send_message("❌ You don't have permission.", ephemeral=True)
            return
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM union_roles WHERE role_name = ?", (role_name,))
            conn.commit()
            conn.close()
            await interaction.response.send_message(f"🗑️ Union role `{role_name}` has been deregistered.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to deregister union role.", ephemeral=True)

    # List union roles
    @app_commands.command(name="list_union_roles", description="List all registered union roles")
    async def list_union_roles(self, interaction: discord.Interaction):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT role_name FROM union_roles")
            roles = cursor.fetchall()
            conn.close()
            if roles:
                role_list = ", ".join(r[0] for r in roles)
                await interaction.response.send_message(f"📜 Registered union roles: {role_list}")
            else:
                await interaction.response.send_message("📭 No union roles registered.")
        except Exception as e:
            print(f"DB ERROR: {e}")
            await interaction.response.send_message("⚠️ Failed to list union roles.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(IGNCommands(bot))

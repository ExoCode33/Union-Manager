import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db_connection(self):
        return sqlite3.connect("database.db")

    @app_commands.command(name="register_ign", description="Register a user's in-game name")
    @app_commands.describe(username="Discord username", ign="In-game name")
    async def register_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("INSERT OR REPLACE INTO users (discord_id, ign, union_name) VALUES (?, ?, COALESCE((SELECT union_name FROM users WHERE discord_id = ?), NULL))", 
                         (str(username.id), ign, str(username.id)))
            conn.commit()
            await interaction.response.send_message(f"✅
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="deregister_ign", description="Remove a user's IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_ign(self, interaction: discord.Interaction, username: discord.Member):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE users SET ign = NULL WHERE discord_id = ?", (str(username.id),))
            if cursor.rowcount > 0:
                conn.commit()
                await interaction.response.send_message(f"✅ IGN for {username.mention} ({username.name}) has been removed", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ No IGN found for {username.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="search_user", description="Search for a user by Discord username")
    @app_commands.describe(username="Discord username to search for")
    async def search_user(self, interaction: discord.Interaction, username: discord.Member):
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT ign_primary, ign_secondary, union_name FROM users WHERE discord_id = ?", (str(username.id),))
            result = cursor.fetchone()
            
            if result:
                ign_primary, ign_secondary, union_name = result
                response = f"**Discord:** {username.mention} ({username.name})\n"
                response += f"**Primary IGN:** {ign_primary if ign_primary else 'Not registered'}\n"
                response += f"**Secondary IGN:** {ign_secondary if ign_secondary else 'Not registered'}\n"
                response += f"**Union:** {union_name if union_name else 'Not assigned'}"
            else:
                response = f"**Discord:** {username.mention} ({username.name})\n**Primary IGN:** Not registered\n**Secondary IGN:** Not registered\n**Union:** Not assigned"
            
            await interaction.response.send_message(response)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error searching user: {str(e)}")
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_connection(self):
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        return conn

    @app_commands.command(name="register_ign", description="Register a user's primary in-game name")
    @app_commands.describe(username="Discord username", ign="Primary in-game name")
    async def register_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (?, ?, 
                        (SELECT ign_secondary FROM users WHERE discord_id = ?),
                        (SELECT union_name FROM users WHERE discord_id = ?))
                ON CONFLICT (discord_id) DO UPDATE
                SET ign_primary = excluded.ign_primary
            """, (str(username.id), ign, str(username.id), str(username.id)))
            conn.commit()

            await interaction.response.send_message(
                f"✅ Primary IGN for {username.mention} ({username.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering primary IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="register_secondary_ign", description="Register a user's secondary in-game name")
    @app_commands.describe(username="Discord username", ign="Secondary in-game name")
    async def register_secondary_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES (?,
                        (SELECT ign_primary FROM users WHERE discord_id = ?),
                        ?, 
                        (SELECT union_name FROM users WHERE discord_id = ?))
                ON CONFLICT (discord_id) DO UPDATE
                SET ign_secondary = excluded.ign_secondary
            """, (str(username.id), str(username.id), ign, str(username.id)))
            conn.commit()

            await interaction.response.send_message(
                f"✅ Secondary IGN for {username.mention} ({username.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering secondary IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="deregister_ign", description="Remove a user's primary IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_ign(self, interaction: discord.Interaction, username: discord.Member):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ign_primary = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            
            if cursor.rowcount > 0:
                await interaction.response.send_message(
                    f"✅ Primary IGN for {username.mention} ({username.name}) has been removed", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No primary IGN found for {username.mention}", ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing primary IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="deregister_secondary_ign", description="Remove a user's secondary IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_secondary_ign(self, interaction: discord.Interaction, username: discord.Member):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ign_secondary = NULL WHERE discord_id = ?", (str(username.id),))
            conn.commit()
            
            if cursor.rowcount > 0:
                await interaction.response.send_message(
                    f"✅ Secondary IGN for {username.mention} ({username.name}) has been removed", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No secondary IGN found for {username.mention}", ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing secondary IGN: {str(e)}", ephemeral=True)
        finally:
            conn.close()

    @app_commands.command(name="search_user", description="Search for a user by Discord username")
    @app_commands.describe(username="Discord username to search for")
    async def search_user(self, interaction: discord.Interaction, username: discord.Member):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ign_primary, ign_secondary, union_name FROM users WHERE discord_id = ?", 
                (str(username.id),)
            )
            row = cursor.fetchone()

            response = f"**Discord:** {username.mention} ({username.name})\n"
            if row:
                response += f"**Primary IGN:** {row['ign_primary'] or 'Not registered'}\n"
                response += f"**Secondary IGN:** {row['ign_secondary'] or 'Not registered'}\n"
                response += f"**Union:** {row['union_name'] or 'Not assigned'}"
            else:
                response += "**Primary IGN:** Not registered\n**Secondary IGN:** Not registered\n**Union:** Not assigned"

            await interaction.response.send_message(response)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error searching user: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))

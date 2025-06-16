import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_primary_ign", description="Register a user's primary in-game name")
    @app_commands.describe(user="Discord user", ign="Primary in-game name")
    async def register_primary_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        conn = await get_connection()
        try:
            # First, check if user exists and get their current data
            existing_user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", str(user.id))
            
            if existing_user:
                # User exists, just update primary IGN
                await conn.execute("UPDATE users SET ign_primary = $1 WHERE discord_id = $2", ign, str(user.id))
            else:
                # User doesn't exist, create new record with primary IGN
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2)
                    VALUES ($1, $2, $3, NULL, NULL, NULL)
                """, str(user.id), user.display_name, ign)

            await interaction.response.send_message(
                f"✅ Primary IGN for {user.mention} ({user.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering primary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="register_secondary_ign", description="Register a user's secondary in-game name")
    @app_commands.describe(user="Discord user", ign="Secondary in-game name")
    async def register_secondary_ign(self, interaction: discord.Interaction, user: discord.Member, ign: str):
        conn = await get_connection()
        try:
            # First, check if user exists and get their current data
            existing_user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", str(user.id))
            
            if existing_user:
                # User exists, just update secondary IGN
                await conn.execute("UPDATE users SET ign_secondary = $1 WHERE discord_id = $2", ign, str(user.id))
            else:
                # User doesn't exist, create new record with secondary IGN
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name, union_name_2)
                    VALUES ($1, $2, NULL, $3, NULL, NULL)
                """, str(user.id), user.display_name, ign)

            await interaction.response.send_message(
                f"✅ Secondary IGN for {user.mention} ({user.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering secondary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_primary_ign", description="Remove a user's primary IGN registration")
    @app_commands.describe(user="Discord user")
    async def deregister_primary_ign(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            result = await conn.execute("UPDATE users SET ign_primary = NULL WHERE discord_id = $1", str(user.id))
            if result and "UPDATE 1" in result:
                await interaction.response.send_message(
                    f"✅ Primary IGN for {user.mention} ({user.name}) has been removed", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No primary IGN found for {user.mention}", ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing primary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_secondary_ign", description="Remove a user's secondary IGN registration")
    @app_commands.describe(user="Discord user")
    async def deregister_secondary_ign(self, interaction: discord.Interaction, user: discord.Member):
        conn = await get_connection()
        try:
            result = await conn.execute("UPDATE users SET ign_secondary = NULL WHERE discord_id = $1", str(user.id))
            if result and "UPDATE 1" in result:
                await interaction.response.send_message(
                    f"✅ Secondary IGN for {user.mention} ({user.name}) has been removed", ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ No secondary IGN found for {user.mention}", ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error removing secondary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.

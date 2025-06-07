import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_ign", description="Register a user's primary in-game name")
    @app_commands.describe(username="Discord username", ign="Primary in-game name")
    async def register_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = await get_connection()
        try:
            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES ($1, $2,
                        (SELECT ign_secondary FROM users WHERE discord_id = $1),
                        (SELECT union_name FROM users WHERE discord_id = $1))
                ON CONFLICT (discord_id) DO UPDATE
                SET ign_primary = EXCLUDED.ign_primary
            """, str(username.id), ign)

            await interaction.response.send_message(
                f"✅ Primary IGN for {username.mention} ({username.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering primary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="register_secondary_ign", description="Register a user's secondary in-game name")
    @app_commands.describe(username="Discord username", ign="Secondary in-game name")
    async def register_secondary_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = await get_connection()
        try:
            await conn.execute("""
                INSERT INTO users (discord_id, ign_primary, ign_secondary, union_name)
                VALUES ($1,
                        (SELECT ign_primary FROM users WHERE discord_id = $1),
                        $2,
                        (SELECT union_name FROM users WHERE discord_id = $1))
                ON CONFLICT (discord_id) DO UPDATE
                SET ign_secondary = EXCLUDED.ign_secondary
            """, str(username.id), ign)

            await interaction.response.send_message(
                f"✅ Secondary IGN for {username.mention} ({username.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering secondary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_ign", description="Remove a user's primary IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_ign(self, interaction: discord.Interaction, username: discord.Member):
        conn = await get_connection()
        try:
            result = await conn.execute("UPDATE users SET ign_primary = NULL WHERE discord_id = $1", str(username.id))
            if result and "UPDATE 1" in result:
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
            await conn.close()

    @app_commands.command(name="deregister_secondary_ign", description="Remove a user's secondary IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_secondary_ign(self, interaction: discord.Interaction, username: discord.Member):
        conn = await get_connection()
        try:
            result = await conn.execute("UPDATE users SET ign_secondary = NULL WHERE discord_id = $1", str(username.id))
            if result and "UPDATE 1" in result:
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
            await conn.close()

    @app_commands.command(name="search_user", description="Search for a user by Discord username")
    @app_commands.describe(username="Discord username to search for")
    async def search_user(self, interaction: discord.Interaction, username: discord.Member):
        conn = await get_connection()
        try:
            row = await conn.fetchrow(
                "SELECT ign_primary, ign_secondary, union_name FROM users WHERE discord_id = $1", str(username.id)
            )

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
            await conn.close()

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))

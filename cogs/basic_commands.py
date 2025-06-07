import discord
from discord.ext import commands
from discord import app_commands
from utils.db import get_connection  # asyncpg connection

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_primary_ign", description="Register a user's primary in-game name")
    @app_commands.describe(username="Discord username", ign="Primary in-game name")
    async def register_primary_ign(self, interaction: discord.Interaction, username: discord.Member, ign: str):
        conn = await get_connection()
        try:
            # First, check if user exists and get their current data
            existing_user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", str(username.id))
            
            if existing_user:
                # User exists, just update primary IGN
                await conn.execute("UPDATE users SET ign_primary = $1 WHERE discord_id = $2", ign, str(username.id))
            else:
                # User doesn't exist, create new record with primary IGN
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name)
                    VALUES ($1, $2, $3, NULL, NULL)
                """, str(username.id), username.display_name, ign)

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
            # First, check if user exists and get their current data
            existing_user = await conn.fetchrow("SELECT * FROM users WHERE discord_id = $1", str(username.id))
            
            if existing_user:
                # User exists, just update secondary IGN
                await conn.execute("UPDATE users SET ign_secondary = $1 WHERE discord_id = $2", ign, str(username.id))
            else:
                # User doesn't exist, create new record with secondary IGN
                await conn.execute("""
                    INSERT INTO users (discord_id, username, ign_primary, ign_secondary, union_name)
                    VALUES ($1, $2, NULL, $3, NULL)
                """, str(username.id), username.display_name, ign)

            await interaction.response.send_message(
                f"✅ Secondary IGN for {username.mention} ({username.name}) set to **{ign}**", ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error registering secondary IGN: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

    @app_commands.command(name="deregister_primary_ign", description="Remove a user's primary IGN registration")
    @app_commands.describe(username="Discord username")
    async def deregister_primary_ign(self, interaction: discord.Interaction, username: discord.Member):
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

    @app_commands.command(name="search_user", description="Search for a user by Discord name, username, ID, or IGN")
    @app_commands.describe(query="Discord name, username, ID, or IGN to search for")
    async def search_user(self, interaction: discord.Interaction, query: str):
        conn = await get_connection()
        try:
            # First try to find by Discord ID (if query is numeric)
            discord_user = None
            if query.isdigit():
                try:
                    discord_user = await self.bot.fetch_user(int(query))
                except:
                    pass
            
            # If not found by ID, try to find by Discord name/username in the guild
            if not discord_user:
                guild = interaction.guild
                if guild:
                    # Search by display name or username
                    for member in guild.members:
                        if (query.lower() in member.display_name.lower() or 
                            query.lower() in member.name.lower() or
                            query.lower() == member.display_name.lower() or
                            query.lower() == member.name.lower()):
                            discord_user = member
                            break
            
            # If found by Discord info, get their data
            if discord_user:
                row = await conn.fetchrow(
                    "SELECT ign_primary, ign_secondary, union_name FROM users WHERE discord_id = $1", 
                    str(discord_user.id)
                )
                
                response = f"**Discord:** {discord_user.mention} ({discord_user.name})\n"
                if row:
                    response += f"**Primary IGN:** {row['ign_primary'] or 'Not registered'}\n"
                    response += f"**Secondary IGN:** {row['ign_secondary'] or 'Not registered'}\n"
                    
                    # Convert union_name to role name if it's a role ID
                    union_display = "Not assigned"
                    if row['union_name']:
                        try:
                            role_id = int(row['union_name'])
                            role = interaction.guild.get_role(role_id)
                            union_display = role.name if role else f"Role ID: {role_id}"
                        except:
                            union_display = row['union_name']
                    
                    response += f"**Union:** {union_display}"
                else:
                    response += "**Primary IGN:** Not registered\n**Secondary IGN:** Not registered\n**Union:** Not assigned"
                
                await interaction.response.send_message(response)
                return
            
            # If not found by Discord info, search by IGN
            rows = await conn.fetch(
                "SELECT discord_id, ign_primary, ign_secondary, union_name FROM users WHERE ign_primary ILIKE $1 OR ign_secondary ILIKE $1", 
                f"%{query}%"
            )
            
            if not rows:
                await interaction.response.send_message(f"❌ No user found matching **{query}**")
                return
            
            if len(rows) == 1:
                # Single result
                row = rows[0]
                try:
                    discord_user = await self.bot.fetch_user(int(row['discord_id']))
                    user_display = f"{discord_user.mention} ({discord_user.name})"
                except:
                    user_display = f"Unknown User (ID: {row['discord_id']})"
                
                # Determine which IGN matched
                matched_ign = ""
                if row['ign_primary'] and query.lower() in row['ign_primary'].lower():
                    matched_ign = f"{row['ign_primary']} (Primary)"
                elif row['ign_secondary'] and query.lower() in row['ign_secondary'].lower():
                    matched_ign = f"{row['ign_secondary']} (Secondary)"
                
                # Convert union_name to role name if it's a role ID
                union_display = "Not assigned"
                if row['union_name']:
                    try:
                        role_id = int(row['union_name'])
                        role = interaction.guild.get_role(role_id)
                        union_display = role.name if role else f"Role ID: {role_id}"
                    except:
                        union_display = row['union_name']
                
                response = f"**Matched IGN:** {matched_ign}\n"
                response += f"**Discord:** {user_display}\n"
                response += f"**Primary IGN:** {row['ign_primary'] or 'Not registered'}\n"
                response += f"**Secondary IGN:** {row['ign_secondary'] or 'Not registered'}\n"
                response += f"**Union:** {union_display}"
                
                await interaction.response.send_message(response)
            else:
                # Multiple results
                response = f"**Multiple users found matching '{query}':**\n\n"
                for i, row in enumerate(rows[:5]):  # Limit to 5 results
                    try:
                        discord_user = await self.bot.fetch_user(int(row['discord_id']))
                        user_display = f"{discord_user.mention} ({discord_user.name})"
                    except:
                        user_display = f"Unknown User (ID: {row['discord_id']})"
                    
                    # Show which IGN matched
                    matched_ign = ""
                    if row['ign_primary'] and query.lower() in row['ign_primary'].lower():
                        matched_ign = row['ign_primary']
                    elif row['ign_secondary'] and query.lower() in row['ign_secondary'].lower():
                        matched_ign = row['ign_secondary']
                    
                    # Convert union_name to role name if it's a role ID
                    union_display = "None"
                    if row['union_name']:
                        try:
                            role_id = int(row['union_name'])
                            role = interaction.guild.get_role(role_id)
                            union_display = role.name if role else f"Role ID: {role_id}"
                        except:
                            union_display = row['union_name']
                    
                    response += f"**{i+1}.** {user_display}\n"
                    response += f"   IGN: {matched_ign} | Union: {union_display}\n\n"
                
                if len(rows) > 5:
                    response += f"*... and {len(rows) - 5} more results*"
                
                await interaction.response.send_message(response)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error searching user: {str(e)}", ephemeral=True)
        finally:
            await conn.close()

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))

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

    @app_commands.command(name="search_user", description="Search for a user by Discord name, username, ID, or IGN")
    @app_commands.describe(query="Discord name, username, ID, or IGN to search for")
    async def search_user(self, interaction: discord.Interaction, query: str):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
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
                cursor.execute(
                    "SELECT ign_primary, ign_secondary, union_name FROM users WHERE discord_id = ?", 
                    (str(discord_user.id),)
                )
                row = cursor.fetchone()
                
                response = f"**Discord:** {discord_user.mention} ({discord_user.name})\n"
                if row:
                    response += f"**Primary IGN:** {row['ign_primary'] or 'Not registered'}\n"
                    response += f"**Secondary IGN:** {row['ign_secondary'] or 'Not registered'}\n"
                    response += f"**Union:** {row['union_name'] or 'Not assigned'}"
                else:
                    response += "**Primary IGN:** Not registered\n**Secondary IGN:** Not registered\n**Union:** Not assigned"
                
                await interaction.response.send_message(response)
                return
            
            # If not found by Discord info, search by IGN
            cursor.execute(
                "SELECT discord_id, ign_primary, ign_secondary, union_name FROM users WHERE ign_primary LIKE ? OR ign_secondary LIKE ?", 
                (f"%{query}%", f"%{query}%")
            )
            rows = cursor.fetchall()
            
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
                
                response = f"**Matched IGN:** {matched_ign}\n"
                response += f"**Discord:** {user_display}\n"
                response += f"**Primary IGN:** {row['ign_primary'] or 'Not registered'}\n"
                response += f"**Secondary IGN:** {row['ign_secondary'] or 'Not registered'}\n"
                response += f"**Union:** {row['union_name'] or 'Not assigned'}"
                
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
                    
                    response += f"**{i+1}.** {user_display}\n"
                    response += f"   IGN: {matched_ign} | Union: {row['union_name'] or 'None'}\n\n"
                
                if len(rows) > 5:
                    response += f"*... and {len(rows) - 5} more results*"
                
                await interaction.response.send_message(response)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error searching user: {str(e)}", ephemeral=True)
        finally:
            conn.close()

async def setup(bot):
    await bot.add_cog(BasicCommands(bot))

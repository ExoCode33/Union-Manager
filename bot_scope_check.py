# bot_scope_check.py - COMPLETE FILE - Run this to check your bot's OAuth scopes

import discord
from discord.ext import commands
import os

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"🔍 Checking bot setup for {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    
    # Generate correct invite link
    permissions = discord.Permissions(
        send_messages=True,
        use_slash_commands=True,
        manage_roles=True,
        read_message_history=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True,
        administrator=True  # For testing
    )
    
    invite_url = discord.utils.oauth_url(
        bot.user.id, 
        permissions=permissions,
        scopes=('bot', 'applications.commands')  # CRITICAL: Both scopes needed
    )
    
    print(f"\n🔗 **CORRECT INVITE URL:**")
    print(f"{invite_url}")
    print(f"\n⚠️ **IMPORTANT:** Your bot MUST be invited with BOTH scopes:")
    print(f"   ✅ 'bot' scope")
    print(f"   ✅ 'applications.commands' scope")
    print(f"\n💡 If your bot was invited without 'applications.commands', you'll get 'Unknown Integration' errors!")
    
    for guild in bot.guilds:
        print(f"\n🏛️ Guild: {guild.name}")
        
        # Check if bot has slash command permissions
        bot_member = guild.get_member(bot.user.id)
        if bot_member:
            perms = bot_member.guild_permissions
            print(f"   📋 Bot permissions:")
            print(f"     - Use Slash Commands: {perms.use_slash_commands}")
            print(f"     - Send Messages: {perms.send_messages}")
            print(f"     - Manage Roles: {perms.manage_roles}")
            print(f"     - Administrator: {perms.administrator}")
            
            if not perms.use_slash_commands and not perms.administrator:
                print(f"   ❌ PROBLEM: Bot lacks slash command permissions!")
                print(f"   🔧 FIX: Re-invite bot with correct URL above")
        
        # Try to fetch application commands to test scope
        try:
            app_commands = await bot.tree.fetch_commands(guild=guild)
            print(f"   ✅ Can fetch guild commands: {len(app_commands)} found")
        except discord.Forbidden:
            print(f"   ❌ CANNOT fetch guild commands - missing 'applications.commands' scope!")
        except Exception as e:
            print(f"   ⚠️ Error fetching commands: {e}")
    
    print(f"\n🎯 **DIAGNOSIS:**")
    print(f"   If you see 'Unknown Integration' errors:")
    print(f"   1. Bot was invited without 'applications.commands' scope")
    print(f"   2. Use the invite URL above to re-invite your bot")
    print(f"   3. Make sure to check BOTH 'bot' and 'applications.commands'")
    print(f"   4. After re-inviting, restart your bot")
    
    await bot.close()

if __name__ == "__main__":
    print("🔍 Checking bot OAuth scopes and permissions...")
    print("This will generate the correct invite URL for your bot.\n")
    bot.run(TOKEN)

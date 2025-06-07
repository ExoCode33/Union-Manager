# Discord Union Bot

A modular, slash-command Discord bot to manage dual IGN assignments and union roles with comprehensive member management features.

## Features

- **15 Slash Commands** organized across 4 modules
- **Dual IGN Support** (Primary and Secondary in-game names)
- **Role-based Permissions** (Admin and Union Leader restrictions)
- **Auto-detection System** for union leaders
- **Real-time Member Tracking** with crown emojis for leaders
- **Dual IGN Management** system
- **SQLite Persistent Storage**
- **Railway-ready Deployment**

## Quick Setup

1. **Add your bot token** to `.env`
2. **Install requirements**: `pip install -r requirements.txt`
3. **Place command files** in the `cogs/` directory
4. **Run the bot**: `python bot.py`

## File Structure

```
discord-union-bot/
├── bot.py                    # Main entry point
├── cogs/                     # Command modules
│   ├── basic_commands.py     # IGN and user search commands
│   ├── union_management.py   # Union role and leader management
│   ├── union_membership.py   # Member add/remove commands
│   └── union_info.py         # Information display commands
├── utils/                    # Helper utilities
│   └── db.py                 # Database connection
├── db/                       # Database schema (optional setup)
└── requirements.txt          # Python dependencies
```

## Commands Overview

### 📝 Basic Commands (`basic_commands.py`)
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/register_ign` | Register a user's primary in-game name | Anyone |
| `/register_secondary_ign` | Register a user's secondary in-game name | Anyone |
| `/deregister_ign` | Remove a user's primary IGN registration | Anyone |
| `/deregister_secondary_ign` | Remove a user's secondary IGN registration | Anyone |
| `/search_user` | Search for a user by Discord username | Anyone |

### ⚙️ Union Management (`union_management.py`)
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/register_role_as_union` | Register a Discord role as a union | Admin |
| `/deregister_role_as_union` | Deregister a union role | Admin |
| `/appoint_union_leader` | Appoint a union leader | Admin |
| `/dismiss_union_leader` | Dismiss a union leader | Admin |

### 👥 Union Membership (`union_membership.py`)
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/add_user_to_union` | Add user to YOUR union (auto-detects) | Union Leaders |
| `/remove_user_from_union` | Remove user from YOUR union | Union Leaders |
| `/admin_add_user_to_union` | Add user to ANY union | @Admin only |
| `/admin_remove_user_from_union` | Remove user from ANY union | @Admin only |

### 📊 Union Information (`union_info.py`)
| Command | Description | Permissions |
|---------|-------------|-------------|
| `/show_union_leader` | Show all union leaders and their assignments | Anyone |
| `/show_union_detail` | Show all unions with member lists and crown emojis 👑 | Anyone |

## Dual IGN System

### **Primary and Secondary IGNs**
- Each user can register **two in-game names**
- Primary IGN for main account
- Secondary IGN for alternate account
- Both IGNs are preserved when joining/leaving unions
- Display format: `@User (PrimaryIGN | SecondaryIGN)`

### **IGN Management**
```
/register_ign username:Player ign:MainAccount
# ✅ Primary IGN for Player set to MainAccount

/register_secondary_ign username:Player ign:AltAccount
# ✅ Secondary IGN for Player set to AltAccount

/search_user username:Player
# Discord: @Player (player_discord)
# Primary IGN: MainAccount
# Secondary IGN: AltAccount
# Union: Union-ZoxCrusaders
```

## Permission System

### **Union Leaders**
- Can only manage **their assigned union**
- Commands automatically detect which union they lead
- Simple workflow: `/add_user_to_union username:NewMember`

### **Admins (@Admin role)**
- Can manage **any union** using override commands
- Full control over union registration and leadership
- Override commands clearly marked with "(Admin override)"

### **Regular Users**
- Can register/search dual IGNs
- Can view union information
- Cannot manage union membership

## Key Features

### 🎯 **Smart Auto-Detection**
- Union leaders don't need to specify which union - the bot automatically detects their assigned union
- Streamlined workflow for daily union management

### 👑 **Visual Hierarchy**
- Union leaders display with crown emoji (👑) in `/show_union_detail`
- Clear distinction between leaders and members

### 🔒 **Security & Privacy**
- Role-based permissions prevent unauthorized access
- Most commands are ephemeral (only visible to command user)
- Public commands: `/search_user`, `/show_union_leader`, `/show_union_detail`
- Admin overrides are clearly logged

### 📱 **User-Friendly Interface**
- Username autocomplete for easy member selection
- Clear error messages with helpful suggestions
- Dual IGN display with pipe separator (`Primary | Secondary`)

## Database Schema

The bot uses SQLite with the following tables:
- `users` - Stores Discord users, dual IGNs, and union assignments
- `union_roles` - Registered union role IDs
- `union_leaders` - Union leader assignments

## Example Usage

### For Dual IGN Management:
```
/register_ign username:Player ign:MainAccount
# ✅ Primary IGN for Player set to MainAccount

/register_secondary_ign username:Player ign:AltAccount  
# ✅ Secondary IGN for Player set to AltAccount

/search_user username:Player
# Discord: @Player (player_discord)
# Primary IGN: MainAccount
# Secondary IGN: AltAccount
# Union: Union-ZoxCrusaders
```

### For Union Leaders:
```
/add_user_to_union username:NewMember
# ✅ @NewMember added to your union Union-ZoxCrusaders

/remove_user_from_union username:OldMember  
# ✅ @OldMember removed from your union Union-ZoxCrusaders
```

### For Union Display:
```
/show_union_detail
# 🏛️ Union Details
# 
# Union-ZoxCrusaders
# 👑 @Leader (LeaderIGN | LeaderAlt)
# @Member1 (MainIGN | AltIGN)
# @Member2 (OnlyMain)
# @Member3 (Main | Alt)
```

## Installation Files

Download these 4 files and place them in your `cogs/` directory:
1. **basic_commands.py** - Dual IGN and user management
2. **union_management.py** - Union and leader setup  
3. **union_membership.py** - Member add/remove functionality
4. **union_info.py** - Information display commands

## Support

- Supports roles starting with "Union-" prefix
- Compatible with Discord.py 2.0+
- Designed for Railway deployment
- Modular architecture for easy maintenance
- Dual IGN system with primary/secondary support

---

*Built for managing gaming unions with Discord integration and dual account support*

# Discord Union Bot

A modular, slash-command Discord bot to manage IGN assignments and union roles.

## Features

- Slash command support
- Role-restricted permissions
- SQLite persistent storage
- Railway-ready deployment

## Setup (Locally or on Railway)

1. Add your bot token to `.env`
2. Install requirements: `pip install -r requirements.txt`
3. Run the bot: `python bot.py`

## Folder Structure

- `bot.py` - Main entry
- `cogs/` - Slash command modules
- `utils/` - Helper utilities
- `db/` - DB schema (optional setup)

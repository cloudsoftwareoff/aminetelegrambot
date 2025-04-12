# Telegram Bot for Credit Management System

A Python-based Telegram bot for managing user credits, orders, and refill requests.

## Features

- User authentication via unique codes
- Credit management system
- Order processing (25GO/35GO offers)
- Admin dashboard for user/order management
- USDT payment integration for credit refills
- Conversation handlers for smooth user interaction

## Installation

1. Clone the repository:
```bash
git clone https://github.com/cloudsoftwareoff/aminetelegrambot
cd aminetelegrambot
```
2. Install dependencies:
```bash
pip install python-telegram-bot==20.0 sqlite3
```
3. Create a constants.py file with your configuration:

```bash
BOT_TOKEN = "your_bot_token_here"
ADMIN_ID =   # Your Telegram user ID
USDT_WALLET = "your_usdt_wallet_address"

# Conversation states
(IDENTIFY, PHONE, OFFER, REJECT_REASON, ADMIN_ADD_CODE, 
 ADMIN_ADD_CREDITS, ADMIN_ALTER_CREDIT, REFILL_STATE) = range(8)
 ```
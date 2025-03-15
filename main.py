import requests
import json
import time
import os
import socketserver
import threading
import random
import asyncio
import pytz
from datetime import datetime
import dateutil.tz
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict

# Telegram bot token
TELEGRAM_BOT_TOKEN = '7921451194:AAGGAZrp2gtyUuv_KNZCmF3pFa10AEUU3Hc'

# Dictionary to track active SMS sending tasks for each user
active_tasks = {}

# List of approved keys - you can add more keys here
APPROVED_KEYS = ['amirhere', 'mianamir', 'key3', 'key4', 'key5']

# Your WhatsApp contact
WHATSAPP_CONTACT = '+923114397148'

# Dictionary to track user approval status
user_approval_status = {}

# Dictionary to track user statistics
user_stats = defaultdict(lambda: {
    'messages_sent': 0,
    'last_activity': None,
    'running': False
})

class MyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024).strip()
        self.request.sendall(b"TRICKS BY AMIR")

def run_server():
    PORT = int(os.environ.get('PORT', 4000))
    server = socketserver.ThreadingTCPServer(("0.0.0.0", PORT), MyHandler)
    print(f"Server running on port {PORT}")
    server.serve_forever()

async def send_messages_from_file(token, tid, hater_name, speed, file_content, chat_id, context, user_id):
    message_count = 0
    headers = {"Content-Type": "application/json"}

    # Update user stats
    user_stats[user_id]['running'] = True
    user_stats[user_id]['last_activity'] = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")

    messages = [msg.strip() for msg in file_content.split('\n') if msg.strip()]

    try:
        while not context.user_data.get('stop_sending', False):
            for message in messages:
                # Check stop flag again between each message
                if context.user_data.get('stop_sending', False):
                    break

                # If this user's task has been canceled, exit
                if user_id not in active_tasks:
                    return {"status": "canceled", "messages_sent": message_count}

                url = f"https://graph.facebook.com/v17.0/{'t_' + tid}/"
                full_message = hater_name + ' ' + message
                parameters = {'access_token': token, 'message': full_message}

                try:
                    response = requests.post(url, json=parameters, headers=headers)
                    message_count += 1
                    current_time = time.strftime("%Y-%m-%d %I:%M:%S %p")

                    status_message = ""
                    if response.ok:
                        status_message = f"✅ SMS SENT! {message_count} to Convo {tid}: {full_message}"
                        print(f"\033[1;92m[+] CHALA GEYA SMS ✅ {message_count} of Convo {tid}: {full_message}")
                        # Update user stats when message is sent successfully
                        user_stats[user_id]['messages_sent'] += 1
                    else:
                        status_message = f"❌ SMS FAILED! {message_count} to Convo {tid}: {full_message}"
                        print(f"\033[1;91m[x] MSG NAHI JA RAHA HAI ❌ {message_count} of Convo {tid}: {full_message}")

                    # Send real-time update to Telegram
                    if chat_id:
                        await context.bot.send_message(chat_id=chat_id, text=status_message)
                except Exception as e:
                    print(f"Error sending message: {str(e)}")
                    if chat_id:
                        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error sending message: {str(e)}")

                # Wait for specified speed between messages
                try:
                    speed_seconds = float(speed)
                    await asyncio.sleep(speed_seconds)
                except ValueError:
                    await asyncio.sleep(1)  # Default to 1 second if speed is invalid

        await context.bot.send_message(chat_id=chat_id, text=f"🛑 Stopped SMS sending after {message_count} messages.")
    except Exception as e:
        print(f"Error in send_messages: {str(e)}")
        if chat_id:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error in SMS loop: {str(e)}")
    finally:
        # Update user stats
        user_stats[user_id]['running'] = False
        user_stats[user_id]['last_activity'] = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")

        # Clean up active task reference
        if user_id in active_tasks:
            del active_tasks[user_id]
        return {"status": "completed", "messages_sent": message_count}

from fb_token_validator import fetch_group_list

async def generate_key(user_id):
    import random
    key = f"amir{random.randint(10, 99)}"

    # Check if user already has a key
    existing_key = await get_user_key(user_id)
    if existing_key:
        return existing_key

    # Add new key
    with open('users.txt', 'a') as f:
        f.write(f"{user_id}:{key}\n")
    return key

async def get_user_key(user_id):
    try:
        with open('users.txt', 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        uid, key = line.split(':')
                        if str(user_id) == uid:
                            return key.strip()
                    except ValueError:
                        continue
    except FileNotFoundError:
        with open('users.txt', 'w') as f:
            f.write("# User ID : Key mapping\n# Format: user_id:key\n")
    return None

async def is_key_approved(key):
    # First check APPROVED_KEYS list
    if key in APPROVED_KEYS:
        return True

    # Then check approved.txt
    try:
        with open('approved.txt', 'r') as f:
            lines = f.readlines()
            approved_keys = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
            return key in approved_keys
    except FileNotFoundError:
        # Create approved.txt if it doesn't exist
        with open('approved.txt', 'w') as f:
            f.write("# Approved keys\n# One key per line\n")

    return False

async def approve_key(key):
    if not await is_key_approved(key):
        with open('approved.txt', 'a') as f:
            f.write(f"{key}\n")
        return True
    return False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"

    # Reset any previous steps
    context.user_data.clear()

    # Check if user has a key
    user_key = await get_user_key(user_id)

    if not user_key:
        # Generate new key
        user_key = await generate_key(user_id)
        # Add key to users.txt
        with open('users.txt', 'a') as f:
            f.write(f"{user_id}:{user_key}\n")
        welcome_message = f"""
Welcome to the VIP Messenger Convo System Bot! ✨
🔹 Your gateway to seamless communication.
🔹 Designed for premium users like you!

Approved Key: `{user_key}`
Status: 🟡 Pending

🔹 Please wait for approval.
🔹 For assistance, contact WhatsApp: *{WHATSAPP_CONTACT}*

Owner: Mian Amir
"""
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        context.user_data['step'] = 'waiting_for_approval'
        return

    # Check if key is approved
    if await is_key_approved(user_key):
        await update.message.reply_text('You are approved ✅ Please send your Facebook token.')
        context.user_data['step'] = 'waiting_for_token'
    else:
        vip_message = f"""
━━━━━━━━━━━━━━━━━━
🔥 𝑽𝑰𝑷 𝑨𝑪𝑪𝑬𝑺𝑺 𝑹𝑬𝑸𝑼𝑰𝑹𝑬𝑫! 🔥
━━━━━━━━━━━━━━━━━━

🚫 𝑨𝑪𝑪𝑬𝑺𝑺 𝑫𝑬𝑵𝑰𝑬𝑫! 🚫

🔑 Your VIP Key: (`{user_key}`)
⚠️ Status: ❌ 𝐍𝐨𝐭 𝐀𝐩𝐩𝐫𝐨𝐯𝐞𝐝 ❌

📌 𝑷𝒍𝒆𝒂𝒔𝒆 𝑪𝒐𝒏𝒕𝒂𝒄𝒕 𝑻𝒉𝒆 𝑶𝒘𝒏𝑬𝑹 𝑭𝒐𝒓 𝑨𝒑𝒑𝒓𝒐𝒗𝒂𝒍!

📲 𝑾𝒉𝒂𝒕𝒔𝑨𝒑𝒑: *{WHATSAPP_CONTACT}*

🔰 𝑷𝒓𝒆𝒎𝒊𝒖𝒎 𝑼𝒔𝒆𝒓𝒔 𝑶𝒏𝒍𝒚! 🔰

━━━━━━━━━━━━━━━━━━
👑 𝑶𝑾𝑵𝑬𝑹: 𝑴𝑰𝑨𝑵 𝑨𝑴𝑰𝑹 👑
━━━━━━━━━━━━━━━━━━"""
        await update.message.reply_text(vip_message, parse_mode='Markdown')
        context.user_data['step'] = 'waiting_for_approval'

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = """
*Available Commands:*

/start - Start the bot and get your approval key
/help - Show this help message
/status - Check your approval status
/stop - Stop the SMS sending process (Approved users only)

*For Approved Users:*
- Send Facebook token to start sending messages
- Configure speed and message settings
- Monitor message delivery status
Send me your token, TID, speed, hater name, and message file to send SMS.

Commands:
/start - Start the bot
/help - Show this help message
/stop - Stop the SMS sending process
/status - Check your stats and active users

For approval or support, contact on WhatsApp:
📱 *""" + WHATSAPP_CONTACT + """*

The bot will continuously send messages in a loop until you send the /stop command.
"""
    await update.message.reply_text(help_text)

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if user has a key and is approved
    user_key = await get_user_key(user_id)
    if not user_key or not await is_key_approved(user_key):
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    # Set stop flag for this specific user
    context.user_data['stop_sending'] = True

    # Preserve approval status while stopping
    if 'token' in context.user_data:
        stored_token = context.user_data['token']
        context.user_data.clear()
        context.user_data['token'] = stored_token
        context.user_data['stop_sending'] = True

    # Kill the user's task if it exists
    if user_id in active_tasks:
        await update.message.reply_text('🛑 Stopping your SMS sending process. Please wait...')
        del active_tasks[user_id]
    else:
        await update.message.reply_text('ℹ️ You don\'t have any active SMS sending process.')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_key = await get_user_key(user_id)

    if not user_key:
        await update.message.reply_text("⚠️ You haven't started the bot yet. Use /start to begin.")
        return

    is_approved = await is_key_approved(user_key)
    status_emoji = "✅" if is_approved else "🟡"
    status_text = "Approved" if is_approved else "Pending"

    status_message = f"""
*Bot Status Report* 📊

*Your Status:*
Key: `{user_key}`
Status: {status_emoji} {status_text}
"""

    if is_approved:
        # Get current active users count
        active_users = sum(1 for uid, stats in user_stats.items() if stats['running'])

        # Get user's own stats
        user_messages = user_stats[user_id]['messages_sent']
        last_activity = user_stats[user_id]['last_activity'] or "Never"

        status_message += f"""
*Your Stats:*
Messages Sent: {user_messages}
Last Activity: {last_activity}

*System Stats:*
Active Users: {active_users}/50
"""

    status_message += f"""
*Support:*
WhatsApp: *{WHATSAPP_CONTACT}*
Owner: *Mian Amir*
    """

    await update.message.reply_text(status_message, parse_mode='Markdown')

async def add_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Get the user's ID
    user_id = update.effective_user.id

    # Check if the message starts with /addkey
    if not update.message.text.startswith('/addkey '):
        await update.message.reply_text('Usage: /addkey <new_key>')
        return

    # Extract the new key from the message
    new_key = update.message.text.split(' ', 1)[1].strip()

    # Check if the key already exists
    if new_key in APPROVED_KEYS:
        await update.message.reply_text(f'The key \'{new_key}\' already exists!')
        return

    # Add the new key to the list
    APPROVED_KEYS.append(new_key)
    await update.message.reply_text(f'Key \'{new_key}\' added successfully!')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Handle approval key verification
    if 'step' in context.user_data and context.user_data['step'] == 'waiting_for_approval':
        approval_key = update.message.text.strip()

        # Store user key mapping regardless of approval status
        if not await get_user_key(user_id):
            with open('users.txt', 'a') as f:
                f.write(f"{user_id}:{approval_key}\n")

        if await is_key_approved(approval_key):
            # Clear context but preserve approval
            stored_token = context.user_data.get('token', None)
            context.user_data.clear()
            if stored_token:
                context.user_data['token'] = stored_token

            await update.message.reply_text('✅ Your key has been approved! You can now use the bot.')
            await update.message.reply_text('Please send your token.')
            context.user_data['step'] = 'waiting_for_token'
        else:
            await update.message.reply_text('❌ Invalid approval key. Please contact the admin on WhatsApp:')
            await update.message.reply_text(f'📱 {WHATSAPP_CONTACT}')
        return

    # Get user's key and check approval
    user_key = await get_user_key(user_id)
    if not user_key or not await is_key_approved(user_key):
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    if 'step' not in context.user_data:
        context.user_data['step'] = 'waiting_for_token'

    if context.user_data['step'] == 'waiting_for_token':
        token = update.message.text.strip()
        try:
            # Fetch and display groups using token.py functionality
            groups = await fetch_group_list(token)

            # Store token for later use
            context.user_data['token'] = token

            # Format group list message
            group_list = "*Available Groups:*\n\n"
            for i, group in enumerate(groups, 1):
                group_list += f"{i}. *{group['name']}*\nTID: `{group['id']}`\n\n"

            await update.message.reply_text(group_list, parse_mode='Markdown')
            await update.message.reply_text('Please send the TID you want to use from the list above.')
            context.user_data['step'] = 'waiting_for_tid'

        except Exception as e:
            await update.message.reply_text(f"⚠️ Error verifying token: {str(e)}\nPlease check your token and try again.")

    elif context.user_data['step'] == 'waiting_for_tid':
        context.user_data['tid'] = update.message.text
        await update.message.reply_text('TID received. Now please send the speed (in seconds between messages).')
        context.user_data['step'] = 'waiting_for_speed'

    elif context.user_data['step'] == 'waiting_for_speed':
        context.user_data['speed'] = update.message.text
        await update.message.reply_text('Speed received. Now please send the hater\'s name.')
        context.user_data['step'] = 'waiting_for_hater_name'

    elif context.user_data['step'] == 'waiting_for_hater_name':
        context.user_data['hater_name'] = update.message.text
        await update.message.reply_text('Hater name received. Now please send the text file or paste your messages.')
        context.user_data['step'] = 'waiting_for_file_content'

    elif context.user_data['step'] == 'waiting_for_file_content':
        context.user_data['file_content'] = update.message.text
        username = update.effective_user.username or "User"
        current_time = datetime.now(pytz.timezone('Asia/Karachi')).strftime("%Y-%m-%d %I:%M:%S %p")

        start_message = f"""
*SMS Sending Started* ✅
*User:* {username}
*Time:* {current_time}
*TID:* {context.user_data['tid']}
*Speed:* {context.user_data['speed']} seconds

This will continue looping until you send /stop command.
For any issues, contact on WhatsApp: *{WHATSAPP_CONTACT}*
        """

        await update.message.reply_text(start_message, parse_mode='Markdown')

        # Reset the user-specific stop flag before starting
        context.user_data['stop_sending'] = False

        # Get the user's ID
        user_id = update.effective_user.id

        # Stop any existing task for this user
        if user_id in active_tasks:
            context.user_data['stop_sending'] = True
            # Small wait to ensure the task sees the stop signal
            await asyncio.sleep(0.5)

        # Start SMS sending in a separate task to avoid blocking the bot
        chat_id = update.effective_chat.id
        sms_task = asyncio.create_task(
            send_messages_from_file(
                context.user_data['token'],
                context.user_data['tid'],
                context.user_data['hater_name'],
                context.user_data['speed'],
                context.user_data['file_content'],
                chat_id,
                context,
                user_id
            )
        )

        # Store the task reference
        active_tasks[user_id] = sms_task

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    # Check if user has a key and is approved
    user_key = await get_user_key(user_id)
    if not user_key or not await is_key_approved(user_key):
        await update.message.reply_text("You need to be approved to use this service. Use /start to begin the approval process.")
        return

    if 'step' not in context.user_data or context.user_data['step'] != 'waiting_for_file_content':
        await update.message.reply_text('Please first send token, TID, speed, and hater name.')
        return

    file = await update.message.document.get_file()

    # Download the file and read its contents
    file_content = ""
    try:
        file_bytes = await file.download_as_bytearray()
        file_content = file_bytes.decode('utf-8')
    except Exception as e:
        await update.message.reply_text(f'Error reading file: {str(e)}')
        return

    await update.message.reply_text('File received. Starting to send SMS. This will continue looping until you send /stop command.')

    # Reset the user-specific stop flag before starting
    context.user_data['stop_sending'] = False

    # Get the user's ID
    user_id = update.effective_user.id

    # Stop any existing task for this user
    if user_id in active_tasks:
        context.user_data['stop_sending'] = True
        # Small wait to ensure the task sees the stop signal
        await asyncio.sleep(0.5)

    # Start SMS sending in a separate task to avoid blocking the bot
    chat_id = update.effective_chat.id
    sms_task = asyncio.create_task(
        send_messages_from_file(
            context.user_data['token'],
            context.user_data['tid'],
            context.user_data['hater_name'],
            context.user_data['speed'],
            file_content,
            chat_id,
            context,
            user_id
        )
    )

    # Store the task reference
    active_tasks[user_id] = sms_task

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    print(f"Update caused error: {context.error}")
    if isinstance(update, Update) and update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"⚠️ An error occurred: {context.error}"
        )

def main() -> None:
    # Create the Application and pass the bot token
    builder = Application.builder()
    application = builder.token(TELEGRAM_BOT_TOKEN).build()

    # Start the server in a separate thread
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stop", stop_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("addkey", add_key))

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    print("Bot started, press Ctrl+C to stop")

    # Configure more robust polling
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        pool_timeout=30,
        read_timeout=30,
        write_timeout=30,
        connect_timeout=30
    )

if __name__ == "__main__":
    main()
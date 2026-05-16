import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import BOT_TOKEN, CHANNELS, REGISTRATION_LINK

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    server = HTTPServer(("0.0.0.0", 8080), HealthHandler)
    server.serve_forever()


async def check_membership(bot, user_id: int, channel: dict) -> bool:
    if not channel.get("check", True):
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
        return member.status in [
            ChatMember.MEMBER,
            ChatMember.ADMINISTRATOR,
            ChatMember.OWNER,
        ]
    except Exception as e:
        logger.error(f"Error checking membership for {channel['id']}: {e}")
        return False


def build_channels_keyboard(joined_statuses: list[bool]) -> InlineKeyboardMarkup:
    buttons = []
    for i, channel in enumerate(CHANNELS):
        status_icon = "✅" if joined_statuses[i] else "🔗"
        buttons.append(
            [InlineKeyboardButton(
                f"{status_icon} {channel['name']}",
                url=channel["url"]
            )]
        )

    if all(joined_statuses):
        buttons.append([InlineKeyboardButton("🎉 Get Registration Link", callback_data="get_link")])
    else:
        buttons.append([InlineKeyboardButton("✔️ Check Membership", callback_data="check")])

    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id

    statuses = [
        await check_membership(context.bot, user_id, ch)
        for ch in CHANNELS
    ]

    all_joined = all(statuses)

    if all_joined:
        await update.message.reply_text(
            f"👋 Welcome back, {user.first_name}!\n\n"
            f"✅ You're already subscribed to all required channels.\n\n"
            f"🔗 Here is your registration link:\n{REGISTRATION_LINK}",
        )
        return

    keyboard = build_channels_keyboard(statuses)
    await update.message.reply_text(
        f"👋 Hello, {user.first_name}!\n\n"
        f"To receive the registration link, please join the following channels first:\n",
        reply_markup=keyboard,
    )


async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("Checking your memberships...")

    user_id = query.from_user.id

    statuses = [
        await check_membership(context.bot, user_id, ch)
        for ch in CHANNELS
    ]

    all_joined = all(statuses)

    if all_joined:
        await query.edit_message_text(
            "✅ You've joined all required channels!\n\n"
            "Click the button below to get your registration link 👇",
            reply_markup=build_channels_keyboard(statuses),
        )
    else:
        not_joined = [CHANNELS[i]["name"] for i, s in enumerate(statuses) if not s]
        await query.edit_message_text(
            f"❌ You haven't joined all channels yet.\n\n"
            f"Still need to join: {', '.join(not_joined)}\n\n"
            f"Click the channel buttons below to join, then press Check again.",
            reply_markup=build_channels_keyboard(statuses),
        )


async def get_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    statuses = [
        await check_membership(context.bot, user_id, ch)
        for ch in CHANNELS
    ]

    if all(statuses):
        await query.edit_message_text(
            f"🎉 Congratulations! You're all set.\n\n"
            f"{REGISTRATION_LINK}\n\n"
            f"Good luck!"
        )
    else:
        not_joined = [CHANNELS[i]["name"] for i, s in enumerate(statuses) if not s]
        await query.edit_message_text(
            f"⚠️ Verification failed. You left some channels.\n\n"
            f"Please rejoin: {', '.join(not_joined)}",
            reply_markup=build_channels_keyboard(statuses),
        )


def main() -> None:
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="^check$"))
    app.add_handler(CallbackQueryHandler(get_link_callback, pattern="^get_link$"))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
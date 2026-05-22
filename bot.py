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

# ── Translations ──────────────────────────────────────────────────────────────
TEXTS = {
    "en": {
        "choose_lang":    "🌐 Please choose your language:",
        "welcome":        "👋 Hello, {name}!\n\nTo receive the registration link, please join the channels below first:",
        "already":        "👋 Welcome back, {name}!\n\n✅ You're already subscribed to all channels.\n\n🔗 Registration link:\n{link}",
        "check_btn":      "✔️ Check Membership",
        "get_btn":        "🎉 Get Registration Link",
        "checking":       "Checking your memberships...",
        "all_joined":     "✅ You've joined all required channels!\n\nClick the button below to get your registration link 👇",
        "not_joined":     "❌ You haven't joined all channels yet.\n\nStill need to join: {channels}\n\nJoin them and press Check again.",
        "congrats":       "🎉 Congratulations! You're all set.\n\n{link}\n\nGood luck! 🚀",
        "verify_fail":    "⚠️ Verification failed. You left some channels.\n\nPlease rejoin: {channels}",
    },
    "ru": {
        "choose_lang":    "🌐 Пожалуйста, выберите язык:",
        "welcome":        "👋 Привет, {name}!\n\nЧтобы получить ссылку на регистрацию, сначала вступите в каналы ниже:",
        "already":        "👋 С возвращением, {name}!\n\n✅ Вы уже подписаны на все каналы.\n\n🔗 Ссылка на регистрацию:\n{link}",
        "check_btn":      "✔️ Проверить подписку",
        "get_btn":        "🎉 Получить ссылку",
        "checking":       "Проверяем подписки...",
        "all_joined":     "✅ Вы вступили во все каналы!\n\nНажмите кнопку ниже, чтобы получить ссылку 👇",
        "not_joined":     "❌ Вы ещё не вступили во все каналы.\n\nОсталось вступить: {channels}\n\nВступите и нажмите Проверить снова.",
        "congrats":       "🎉 Поздравляем! Всё готово.\n\n{link}\n\nУдачи! 🚀",
        "verify_fail":    "⚠️ Проверка не прошла. Вы покинули некоторые каналы.\n\nПожалуйста, вступите снова: {channels}",
    },
    "uz": {
        "choose_lang":    "🌐 Iltimos, tilni tanlang:",
        "welcome":        "👋 Salom, {name}!\n\nRo'yxatdan o'tish havolasini olish uchun avval quyidagi kanallarga a'zo bo'ling:",
        "already":        "👋 Qaytib keldingiz, {name}!\n\n✅ Siz allaqachon barcha kanallarga a'zo bo'lgansiz.\n\n🔗 Ro'yxatdan o'tish havolasi:\n{link}",
        "check_btn":      "✔️ A'zolikni tekshirish",
        "get_btn":        "🎉 Havolani olish",
        "checking":       "A'zolik tekshirilmoqda...",
        "all_joined":     "✅ Siz barcha kanallarga a'zo bo'ldingiz!\n\nHavolani olish uchun quyidagi tugmani bosing 👇",
        "not_joined":     "❌ Siz hali barcha kanallarga a'zo bo'lmadingiz.\n\nQolganlar: {channels}\n\nA'zo bo'ling va Tekshirish tugmasini bosing.",
        "congrats":       "🎉 Tabriklaymiz! Hamma narsa tayyor.\n\n{link}\n\nOmad! 🚀",
        "verify_fail":    "⚠️ Tekshiruv muvaffaqiyatsiz. Siz ba'zi kanallardan chiqdingiz.\n\nIltimos, qayta qo'shiling: {channels}",
    },
}

def t(lang: str, key: str, **kwargs) -> str:
    text = TEXTS.get(lang, TEXTS["en"]).get(key, "")
    return text.format(**kwargs) if kwargs else text

def get_lang(context: ContextTypes.DEFAULT_TYPE) -> str:
    return context.user_data.get("lang", "en")


# ── Health check server ───────────────────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, format, *args):
        pass

def run_health_server():
    HTTPServer(("0.0.0.0", 8080), HealthHandler).serve_forever()


# ── Helpers ───────────────────────────────────────────────────────────────────
async def check_membership(bot, user_id: int, channel: dict) -> bool:
    if not channel.get("check", True):
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.error(f"Error checking {channel['id']}: {e}")
        return False

def build_channels_keyboard(joined_statuses: list, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, channel in enumerate(CHANNELS):
        icon = "🔗" if joined_statuses[i] else "🔗"
        buttons.append([InlineKeyboardButton(f"{icon} {channel['name']}", url=channel["url"])])
    if all(joined_statuses):
        buttons.append([InlineKeyboardButton(t(lang, "get_btn"), callback_data="get_link")])
    else:
        buttons.append([InlineKeyboardButton(t(lang, "check_btn"), callback_data="check")])
    return InlineKeyboardMarkup(buttons)

def lang_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇬🇧 English", callback_data="lang_en"),
    ]])


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("lang", None)
    await update.message.reply_text(
        TEXTS["en"]["choose_lang"] + "\n" + TEXTS["ru"]["choose_lang"] + "\n" + TEXTS["uz"]["choose_lang"],
        reply_markup=lang_keyboard(),
    )

async def lang_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    context.user_data["lang"] = lang

    user = query.from_user
    statuses = [await check_membership(context.bot, user.id, ch) for ch in CHANNELS]

    if all(statuses):
        await query.edit_message_text(t(lang, "already", name=user.first_name, link=REGISTRATION_LINK))
        return

    await query.edit_message_text(
        t(lang, "welcome", name=user.first_name),
        reply_markup=build_channels_keyboard(statuses, lang),
    )

async def check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    lang = get_lang(context)
    await query.answer(t(lang, "checking"))

    statuses = [await check_membership(context.bot, query.from_user.id, ch) for ch in CHANNELS]

    if all(statuses):
        await query.edit_message_text(t(lang, "all_joined"), reply_markup=build_channels_keyboard(statuses, lang))
    else:
        missing = ", ".join(CHANNELS[i]["name"] for i, s in enumerate(statuses) if not s)
        await query.edit_message_text(t(lang, "not_joined", channels=missing), reply_markup=build_channels_keyboard(statuses, lang))

async def get_link_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    lang = get_lang(context)
    await query.answer()

    statuses = [await check_membership(context.bot, query.from_user.id, ch) for ch in CHANNELS]

    if all(statuses):
        await query.edit_message_text(t(lang, "congrats", link=REGISTRATION_LINK))
    else:
        missing = ", ".join(CHANNELS[i]["name"] for i, s in enumerate(statuses) if not s)
        await query.edit_message_text(t(lang, "verify_fail", channels=missing), reply_markup=build_channels_keyboard(statuses, lang))


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(lang_callback, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(check_callback, pattern="^check$"))
    app.add_handler(CallbackQueryHandler(get_link_callback, pattern="^get_link$"))

    logger.info("Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
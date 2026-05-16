# ============================================================
#  BOT CONFIGURATION — edit these values before running
# ============================================================

# 1. Your bot token from @BotFather
BOT_TOKEN = "8988853545:AAFyCWL8ve15MPMR3yZKtQfLNovtgnS5lX0"

# 2. The registration link sent after the user joins all channels
REGISTRATION_LINK = "https://new-form-project-37c3ad.zapier.app/cau-international-olympiad-2026"

# 3. The two channels users must join.
CHANNELS = [
    {
        "id": "@ilmiyAcademy",
        "name": "Ilmiy Academy",
        "url": "https://t.me/ilmiyAcademy",
    },
    {
        "id": "@centralasianuni",
        "name": "Central Asian University",
        "url": "https://t.me/centralasianuni",
    },
]

# ============================================================
#  NOTES
#  • The bot MUST be an Administrator in each channel so it
#    can call getChatMember to verify membership.
#  • For private channels use the numeric chat ID, e.g.:
#      "id": -1001234567890
# ============================================================

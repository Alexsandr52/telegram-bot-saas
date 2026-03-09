"""
Inline keyboards for Platform Bot
"""
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)


# ============================================
# Main Menu
# ============================================

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🤖 Мои боты",
                callback_data="my_bots"
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить бота",
                callback_data="add_bot"
            )
        ],
        [
            InlineKeyboardButton(
                text="💳 Подписка",
                callback_data="subscription"
            )
        ],
        [
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data="statistics"
            )
        ],
        [
            InlineKeyboardButton(
                text="⚙️ Настройки",
                callback_data="settings"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Bot Actions
# ============================================

def get_bot_actions_keyboard(bot_id: str) -> InlineKeyboardMarkup:
    """Keyboard for bot actions"""
    buttons = [
        [
            InlineKeyboardButton(
                text="📝 Услуги",
                callback_data=f"bot_services:{bot_id}"
            ),
            InlineKeyboardButton(
                text="📅 График",
                callback_data=f"bot_schedule:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Клиенты",
                callback_data=f"bot_clients:{bot_id}"
            ),
            InlineKeyboardButton(
                text="📋 Записи",
                callback_data=f"bot_appointments:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔄 Перезапустить",
                callback_data=f"bot_restart:{bot_id}"
            ),
            InlineKeyboardButton(
                text="⏹️ Остановить",
                callback_data=f"bot_stop:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="my_bots"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_bots_list_keyboard(bots: list) -> InlineKeyboardMarkup:
    """
    Keyboard with list of user's bots

    Args:
        bots: List of bot dictionaries with 'id', 'bot_username', 'bot_name' keys
    """
    buttons = []

    for bot in bots:
        bot_name = bot.get('bot_name') or bot.get('bot_username', 'Unnamed')
        status_emoji = "🟢" if bot.get('is_active') else "🔴"

        buttons.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {bot_name}",
                callback_data=f"bot_menu:{bot['id']}"
            )
        ])

    # Add action buttons
    buttons.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить нового бота",
                callback_data="add_bot"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 В главное меню",
                callback_data="main_menu"
            )
        ],
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Subscription
# ============================================

def get_subscription_keyboard(current_plan: str = None) -> InlineKeyboardMarkup:
    """Keyboard for subscription plans"""
    buttons = [
        [
            InlineKeyboardButton(
                text="🆓 Free" + (" ✓" if current_plan == "free" else ""),
                callback_data="plan_free"
            )
        ],
        [
            InlineKeyboardButton(
                text="⭐ Pro — 490₽/мес" + (" ✓" if current_plan == "pro" else ""),
                callback_data="plan_pro"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚀 Business — 1990₽/мес" + (" ✓" if current_plan == "business" else ""),
                callback_data="plan_business"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="main_menu"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_payment_keyboard(amount: int, payment_url: str = None) -> InlineKeyboardMarkup:
    """Keyboard for payment"""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"💳 Оплатить {amount}₽",
                url=payment_url
            ) if payment_url else InlineKeyboardButton(
                text="💳 Оформить подписку",
                callback_data="payment_init"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="subscription"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Confirmation
# ============================================

def get_confirmation_keyboard(action: str, item_id: str) -> InlineKeyboardMarkup:
    """
    Generic confirmation keyboard

    Args:
        action: Action being confirmed (e.g., 'delete_bot', 'stop_bot')
        item_id: ID of item being acted upon
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="✅ Да, подтвердить",
                callback_data=f"confirm:{action}:{item_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data="cancel"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Settings
# ============================================

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Settings menu keyboard"""
    buttons = [
        [
            InlineKeyboardButton(
                text="👤 Профиль",
                callback_data="settings_profile"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔔 Уведомления",
                callback_data="settings_notifications"
            )
        ],
        [
            InlineKeyboardButton(
                text="🌐 Язык",
                callback_data="settings_language"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="main_menu"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Reply Keyboards (for text input)
# ============================================

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with cancel button"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )


def get_remove_keyboard() -> ReplyKeyboardRemove:
    """Remove custom keyboard"""
    return ReplyKeyboardRemove()


# ============================================
# Helper Functions
# ============================================

def create_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Create keyboard with just a back button"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
        ]
    )

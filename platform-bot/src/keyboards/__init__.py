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
                text="🌐 Веб-панель",
                callback_data="web_panel"
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


# ============================================
# Services Management
# ============================================

def get_services_list_keyboard(bot_id: str, services: list = None) -> InlineKeyboardMarkup:
    """
    Keyboard for services list

    Args:
        bot_id: Bot UUID
        services: List of service dictionaries
    """
    buttons = []

    if services:
        # Add service buttons
        for service in services:
            service_id = str(service['id'])
            name = service['name']
            status = "✅" if service['is_active'] else "❌"

            buttons.append([
                InlineKeyboardButton(
                    text=f"{status} {name}",
                    callback_data=f"edit_service:{service_id}"
                )
            ])

    # Add action buttons
    buttons.extend([
        [
            InlineKeyboardButton(
                text="➕ Добавить услугу",
                callback_data=f"add_service:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад к боту",
                callback_data=f"bot_menu:{bot_id}"
            )
        ],
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_service_management_keyboard(service_id: str) -> InlineKeyboardMarkup:
    """
    Keyboard for service management (edit/delete)

    Args:
        service_id: Service UUID
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="🔄 Сменить статус",
                callback_data=f"service_toggle_active:{service_id}"
            ),
            InlineKeyboardButton(
                text="✏️ Изменить",
                callback_data=f"service_edit_fields:{service_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="❌ Удалить",
                callback_data=f"delete_service:{service_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_services"
            )
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Schedule Management
# ============================================

def get_schedule_menu_keyboard() -> InlineKeyboardMarkup:
    """Schedule management menu keyboard"""
    buttons = [
        [
            InlineKeyboardButton(
                text="📊 Просмотр",
                callback_data="view_schedule"
            )
        ],
        [
            InlineKeyboardButton(
                text="🕐 Рабочие часы",
                callback_data="set_working_hours"
            )
        ],
        [
            InlineKeyboardButton(
                text="🚫 Выходные/исключения",
                callback_data="add_exception"
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


def get_days_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for selecting day of week"""
    buttons = [
        [
            InlineKeyboardButton(text="Понедельник", callback_data="set_day:1"),
            InlineKeyboardButton(text="Вторник", callback_data="set_day:2")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="set_day:3"),
            InlineKeyboardButton(text="Четверг", callback_data="set_day:4")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="set_day:5"),
            InlineKeyboardButton(text="Суббота", callback_data="set_day:6")
        ],
        [
            InlineKeyboardButton(text="Воскресенье", callback_data="set_day:7"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="manage_schedule")
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

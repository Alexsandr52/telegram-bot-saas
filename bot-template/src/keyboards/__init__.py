"""
Keyboards for Bot Template
Main menu and inline keyboards
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
from typing import List, Dict


# ============================================
# Main Menu Keyboard
# ============================================

def get_main_menu_keyboard(custom_commands: List[dict] = None) -> InlineKeyboardMarkup:
    """
    Generate main menu keyboard with custom commands

    Args:
        custom_commands: List of custom commands from bot config

    Returns:
        Inline keyboard with menu items
    """
    buttons = []

    # Add custom commands (catalog, about, etc.)
    if custom_commands:
        for cmd in custom_commands:
            if not cmd.get('enabled', True):
                continue

            # Map handler types to icons
            icons = {
                'catalog': '📋',
                'about': 'ℹ️',
                'custom': '🔧'
            }
            icon = icons.get(cmd['handler_type'], '📌')

            buttons.append([
                InlineKeyboardButton(
                    text=f"{icon} {cmd['description']}",
                    callback_data=f"cmd_{cmd['command']}"
                )
            ])

    # Default commands
    buttons.extend([
        [
            InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Services Keyboard (Catalog)
# ============================================

def get_services_keyboard(services: List[dict]) -> InlineKeyboardMarkup:
    """
    Generate keyboard with services list

    Args:
        services: List of service dicts

    Returns:
        Inline keyboard with services
    """
    buttons = []

    for service in services:
        price = service.get('price', 0)
        duration = service.get('duration_minutes', 0)
        name = service.get('name', 'Услуга')

        text = f"{name} - {price}₽ ({duration} мин)"
        buttons.append([
            InlineKeyboardButton(
                text=text,
                callback_data=f"service_{service['id']}"
            )
        ])

    # Add back button
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Date Selection Keyboard
# ============================================

def get_dates_keyboard(days: int = 7) -> InlineKeyboardMarkup:
    """
    Generate keyboard with dates for selection

    Args:
        days: Number of days to show

    Returns:
        Inline keyboard with dates
    """
    buttons = []
    today = datetime.now().date()

    # Generate rows with 3 dates each
    row = []
    for i in range(days):
        date = today + timedelta(days=i)
        date_str = date.strftime('%d.%m')

        # Format day name
        day_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        day_name = day_names[date.weekday()]

        # Add emoji for today/tomorrow
        if i == 0:
            text = f"📅 Сегодня ({day_name})"
        elif i == 1:
            text = f"📅 Завтра ({day_name})"
        else:
            text = f"📅 {date_str} ({day_name})"

        row.append(InlineKeyboardButton(
            text=text,
            callback_data=f"date_{date.isoformat()}"
        ))

        # New row every 3 dates
        if len(row) == 3:
            buttons.append(row)
            row = []

    # Add remaining dates
    if row:
        buttons.append(row)

    # Add back button
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="catalog")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Time Slots Keyboard
# ============================================

def get_time_slots_keyboard(
    slots: List[dict],
    selected_date: str,
    service_id: str
) -> InlineKeyboardMarkup:
    """
    Generate keyboard with available time slots

    Args:
        slots: List of slot dicts with start_time, end_time, is_available
        selected_date: Selected date (ISO format)
        service_id: Service ID

    Returns:
        Inline keyboard with time slots
    """
    buttons = []

    # Group slots by availability
    available_slots = [s for s in slots if s.get('is_available', False)]

    if not available_slots:
        buttons.append([
            InlineKeyboardButton(
                text="😔 Нет доступных слотов",
                callback_data="no_slots"
            )
        ])
    else:
        # Create rows with 3 time slots each
        row = []
        for slot in available_slots:
            start_time = slot['start_time'].strftime('%H:%M')
            end_time = slot['end_time'].strftime('%H:%M')

            row.append(InlineKeyboardButton(
                text=f"🕐 {start_time} - {end_time}",
                callback_data=f"slot_{slot['start_time'].isoformat()}_{slot['end_time'].isoformat()}"
            ))

            if len(row) == 3:
                buttons.append(row)
                row = []

        # Add remaining slots
        if row:
            buttons.append(row)

    # Add date selection button and back
    buttons.extend([
        [
            InlineKeyboardButton(text="📅 Выбрать другую дату", callback_data="select_date")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Confirmation Keyboard
# ============================================

def get_confirmation_keyboard(
    service_name: str,
    date: str,
    time: str,
    price: float
) -> InlineKeyboardMarkup:
    """
    Generate keyboard for appointment confirmation

    Args:
        service_name: Service name
        date: Date string
        time: Time string
        price: Service price

    Returns:
        Inline keyboard with confirm/cancel
    """
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвердить запись", callback_data="confirm_booking"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="main_menu")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Profile Keyboard
# ============================================

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Generate keyboard for user profile"""
    buttons = [
        [
            InlineKeyboardButton(text="📋 Мои записи", callback_data="my_appointments")
        ],
        [
            InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ============================================
# Phone Request Keyboard
# ============================================

def get_phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Generate keyboard for phone number request"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_remove_keyboard() -> ReplyKeyboardMarkup:
    """Remove custom keyboard"""
    from aiogram.types import ReplyKeyboardRemove
    return ReplyKeyboardRemove()


# ============================================
# Help Keyboard
# ============================================

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Generate keyboard for help screen"""
    buttons = [
        [
            InlineKeyboardButton(text="🔙 В главное меню", callback_data="main_menu")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)

import telebot
from django.conf import settings
from .models import TelegramProfile
from .constants import UserSteps 
from .handlers import start, profile, registration, login, password_reset, search, add_place

bot = telebot.TeleBot(settings.BOT_TOKEN)

COMMAND_SWITCHER = {
    'Categoriya': search.start_category_search,
    '👤 Profil': profile.show_profile_menu,
    "🌐 Tilni o'zgartirish": start.change_language_prompt,
    'ℹ️ Bot haqida': start.show_bot_info,
    '⬅️ Bosh menyu': start.show_main_menu,
    '📄 Mening ma\'lumotlarim': profile.show_user_data,
    '⬅️ Chiqish': profile.logout,
    '✅ Kirish': login.start_login,
    '📝 Ro‘yxatdan o‘tish': registration.start_registration,
    '🔑 Parolni unutdingizmi?': password_reset.start_password_reset,
    '❌ Bekor qilish': start.show_main_menu,
    '💼 Tadbirkor bo\'lish': profile.handle_become_entrepreneur,
    '➕ Joy qo\'shish': add_place.start_add_place,
    'Категории': search.start_category_search,
    '👤 Профиль': profile.show_profile_menu,
    "🌐 Сменить язык": start.change_language_prompt,
    'ℹ️ О боте': start.show_bot_info,
    '⬅️ Главное меню': start.show_main_menu,
    '📄 Мои данные': profile.show_user_data,
    '⬅️ Выход': profile.logout,
    '✅ Вход': login.start_login,
    '📝 Регистрация': registration.start_registration,
    '🔑 Забыли пароль?': password_reset.start_password_reset,
    '❌ Отмена': start.show_main_menu,
    '💼 Стать предпринимателем': profile.handle_become_entrepreneur,
    '➕ Добавить место': add_place.start_add_place,
}

STATE_SWITCHER = {
    UserSteps.SELECT_LANGUAGE: start.select_language_by_text,
    UserSteps.REG_WAITING_FOR_FIRST_NAME: registration.process_first_name,
    UserSteps.REG_WAITING_FOR_LAST_NAME: registration.process_last_name,
    UserSteps.REG_WAITING_FOR_EMAIL: registration.process_email,
    UserSteps.REG_WAITING_FOR_PASSWORD: registration.process_password,
    UserSteps.REG_WAITING_FOR_PASSWORD_CONFIRM: registration.process_password_confirm,
    UserSteps.REG_WAITING_FOR_CONFIRMATION_CODE: registration.process_confirmation_code,
    UserSteps.LOGIN_WAITING_FOR_EMAIL: login.process_login_email,
    UserSteps.LOGIN_WAITING_FOR_PASSWORD: login.process_login_password,
    UserSteps.RESET_WAITING_FOR_EMAIL: password_reset.process_email_for_reset,
    UserSteps.RESET_WAITING_FOR_CODE: password_reset.process_restore_code,
    UserSteps.RESET_WAITING_FOR_NEW_PASSWORD: password_reset.process_restore_password,
    UserSteps.RESET_WAITING_FOR_PASSWORD_CONFIRM: password_reset.process_restore_password_confirm,
    UserSteps.SEARCH_WAITING_FOR_CATEGORY: search.process_category_selection,
    UserSteps.SEARCH_WAITING_FOR_LOCATION: search.process_location_step,
    UserSteps.PLACE_ADD_WAITING_FOR_NAME_UZ: add_place.process_place_name_uz,
    UserSteps.PLACE_ADD_WAITING_FOR_NAME_RU: add_place.process_place_name_ru,
    UserSteps.PLACE_ADD_WAITING_FOR_CATEGORY: add_place.process_place_category,
    UserSteps.PLACE_ADD_WAITING_FOR_LOCATION: add_place.process_place_location,
    UserSteps.PLACE_ADD_WAITING_FOR_CONTACT: add_place.process_place_contact,
    UserSteps.PLACE_ADD_WAITING_FOR_DESCRIPTION_UZ: add_place.process_place_description_uz,
    UserSteps.PLACE_ADD_WAITING_FOR_DESCRIPTION_RU: add_place.process_place_description_ru,
    UserSteps.PLACE_ADD_WAITING_FOR_IMAGE: add_place.process_place_image,
    UserSteps.PLACE_ADD_WAITING_FOR_CONFIRMATION: None
}

def text_and_media_handler(message):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id, defaults={'language': 'uz'})

    if message.content_type == 'location':
        if profile.step == UserSteps.SEARCH_WAITING_FOR_LOCATION:
            search.process_location_step(message, bot)
            return
        elif profile.step == UserSteps.PLACE_ADD_WAITING_FOR_LOCATION:
            add_place.process_place_location(message, bot)
            return
        elif profile.step == UserSteps.DEFAULT:
            search.start_search_by_location(message, bot)
            return

    if message.content_type == 'photo':
        if profile.step == UserSteps.PLACE_ADD_WAITING_FOR_IMAGE:
            add_place.process_place_image(message, bot)
            return

    if message.content_type != 'text':
        return

    if message.text == '/start':
        start.handle_start(message, bot)
        return

    func = STATE_SWITCHER.get(profile.step)

    if not func:
        func = COMMAND_SWITCHER.get(message.text)

    if func:
        func(message, bot)
    else:
        start.show_main_menu(message, bot)

def callback_query_handler(call):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=call.message.chat.id)
    bot.answer_callback_query(call.id)

    if call.data.startswith("cat_"):
        search.process_category_selection(call, bot)
    elif call.data.startswith("place_"):
        search.show_paginated_place_callback(call, bot)
    elif call.data == "reshow_categories":
        search.handle_reshow_categories(call, bot)
    elif call.data == "add_place_confirm":
        add_place.process_add_place_confirm(call, bot)
    elif call.data == "add_place_cancel":
        add_place.process_add_place_cancel(call, bot)
    elif call.data in ["back_to_main_from_place", "back_to_main_from_category"]:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        start.show_main_menu(call.message, bot)
    elif call.data == "no_action":
        pass

@bot.message_handler(content_types=['text', 'location', 'photo', 'contact'])
def main_message_dispatcher(message):
    text_and_media_handler(message)

@bot.callback_query_handler(func=lambda call: True)
def main_callback_dispatcher(call):
    callback_query_handler(call)
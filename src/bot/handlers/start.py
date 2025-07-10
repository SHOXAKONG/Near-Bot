from ..models import TelegramProfile
from .. import keyboards, utils
from ..constants import UserSteps


def handle_start(message, bot):
    profile, created = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    if not created and profile.language:
        show_main_menu(message, bot)
    else:
        bot.send_message(message.chat.id, "Tilni tanlang / Выберите язык:",
                         reply_markup=keyboards.get_language_selection_keyboard())
        profile.step = UserSteps.SELECT_LANGUAGE
        profile.save()


def select_language_by_text(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)

    if message.text in ['⬅️ Bosh menyu', '⬅️ Главное меню']:
        show_main_menu(message, bot)
        return

    lang = 'uz' if 'O‘zbek' in message.text else 'ru'
    profile.language = lang
    profile.save()
    bot.send_message(message.chat.id, "✅ Til tanlandi!" if lang == 'uz' else "✅ Язык выбран!")
    show_main_menu(message, bot)


def show_main_menu(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    minimal_text = "Menu"

    bot.send_message(
        message.chat.id,
        minimal_text,
        reply_markup=keyboards.get_main_menu_keyboard(profile)
    )

    profile.step = UserSteps.DEFAULT
    profile.save()


def change_language_prompt(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    bot.send_message(message.chat.id, utils.t(profile, "Yangi tilni tanlang:", "Выберите новый язык:"),
                     reply_markup=keyboards.get_language_selection_keyboard())
    profile.step = UserSteps.SELECT_LANGUAGE
    profile.save()


def show_bot_info(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    info_text_uz = (
        "<b>Assalomu alaykum!</b>\n\n"
        "Bu bot sizga eng yaqin joylarni topishda yordam beradi.\n\n"
        "<b>Asosiy funksiyalar:</b>\n"
        "🔹 <b>Kategoriyalar</b> - Kerakli joy turini tanlab, qidirish.\n"
        "👤 <b>Profil</b> - Tizimga kirish, ro'yxatdan o'tish va o'z ma'lumotlaringizni ko'rish.\n"
        "🌐 <b>Tilni o'zgartirish</b> - O'zbek va rus tillari o'rtasida o'tish.\n\n"
        "Botdan samarali foydalanishingizga tilakdoshmiz!"
    )

    info_text_ru = (
        "<b>Здравствуйте!</b>\n\n"
        "Этот бот поможет вам найти ближайшие места.\n\n"
        "<b>Основные функции:</b>\n"
        "🔹 <b>Категории</b> - Поиск по интересующей вас категории мест.\n"
        "👤 <b>Профиль</b> - Вход, регистрация и просмотр ваших данных.\n"
        "🌐 <b>Сменить язык</b> - Переключение между узбекским и русским языками.\n\n"
        "Желаем вам эффективного использования бота!"
    )

    final_text = utils.t(profile, info_text_uz, info_text_ru)
    bot.send_message(message.chat.id, final_text, parse_mode='HTML')
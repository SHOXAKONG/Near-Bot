from ..models import TelegramProfile
from .. import keyboards, utils, api_client
from .start import show_main_menu


def show_profile_menu(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    # print(profile)
    prompt = utils.t(profile, "Profil", "Профиль")
    markup = keyboards.get_profile_menu_keyboard(profile)
    bot.send_message(message.chat.id, prompt, reply_markup=markup)


def show_user_data(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    if not profile.near_user_id:
        bot.send_message(message.chat.id, utils.t(profile, "Siz tizimga kirmagansiz.", "Вы не вошли в систему."))
        return

    response = api_client.get_user_data_from_api(profile)

    if response and response.status_code == 200:
        api_data = response.json()
        first_name = api_data.get('first_name', '')
        last_name = api_data.get('last_name', '')
        email = api_data.get('email', 'N/A')
        role = api_data.get('role', 'user')

        role_text = utils.t(profile, 'Foydalanuvchi', 'Пользователь')
        if role == 'entrepreneur':
            role_text = utils.t(profile, 'Tadbirkor', 'Предприниматель')

        data_message = (
            f"<b>{utils.t(profile, 'Sizning maʼlumotlaringiz', 'Ваши данные')}:</b>\n\n"
            f"👤 <b>{utils.t(profile, 'Ism, Familiya', 'Имя, Фамилия')}:</b> {first_name} {last_name}\n"
            f"📧 <b>Email:</b> {email}\n"
            f"⭐️ <b>Status:</b> {role_text}"
        )
        bot.send_message(message.chat.id, data_message, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id,
                         utils.t(profile, "❌ Ma'lumotlarni yuklashda xatolik yuz berdi.",
                                 "❌ Произошла ошибка при загрузке данных."))


def logout(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    profile.near_user_id = None
    profile.access_token = None
    profile.refresh_token = None
    profile.save()

    success_message = utils.t(profile, "Siz tizimdan chiqdingiz.", "Вы вышли из системы.")
    bot.send_message(message.chat.id, f"✅ {success_message}")

    show_main_menu(message, bot)


def handle_become_entrepreneur(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    if not profile.near_user_id:
        bot.send_message(message.chat.id, utils.t(profile, "Bu amal uchun avval tizimga kiring.",
                                                  "Для этого действия необходимо войти в систему."))
        return

    processing_message = utils.t(profile, "So'rovingiz qayta ishlanmoqda, iltimos kuting...",
                                 "Ваш запрос обрабатывается, пожалуйста, подождите...")
    bot.send_message(message.chat.id, processing_message)

    response = api_client.become_entrepreneur(profile)

    if response and response.status_code == 200:
        response_data = response.json()
        success_text = response_data.get('message', utils.t(profile, "Tabriklaymiz! So'rovingiz qabul qilindi.",
                                                            "Поздравляем! Ваш запрос принят."))
        bot.send_message(message.chat.id, f"✅ {success_text}")

    else:
        error_text = utils.t(profile, "So'rovni yuborishda xatolik yuz berdi.",
                             "Произошла ошибка при отправке запроса.")
        if response is not None:
            try:
                error_text = response.json().get('detail', error_text)
            except:
                pass
        bot.send_message(message.chat.id, f"❌ {error_text}")

    show_main_menu(message, bot)
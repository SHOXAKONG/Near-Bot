import telebot
from ..models import TelegramProfile
from .. import utils, keyboards, api_client
from ..constants import UserSteps
from .profile import show_profile_menu


def start_password_reset(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    prompt = utils.t(profile, "Parolni tiklash uchun emailingizni kiriting:",
                     "Введите ваш email для восстановления пароля:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.RESET_WAITING_FOR_EMAIL
    profile.temp_data = {}
    profile.save()


def process_email_for_reset(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    email = message.text
    profile.temp_data['email'] = email

    response = api_client.forgot_password(profile.language, email)

    if response and response.status_code == 200:
        bot.send_message(message.chat.id, response.json().get('message', '...'))
        prompt = utils.t(profile, "Emailingizga yuborilgan kodni kiriting:", "Введите код из вашего письма:")
        bot.send_message(message.chat.id, prompt)
        profile.step = UserSteps.RESET_WAITING_FOR_CODE
    else:
        bot.send_message(message.chat.id, utils.t(profile, "❌ Email topilmadi.", "❌ Email не найден."))
        profile.step = UserSteps.DEFAULT
        show_profile_menu(message, bot)

    profile.save()


def process_restore_code(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['code'] = message.text
    prompt = utils.t(profile, "Yangi parol yarating:", "Создайте новый пароль:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.RESET_WAITING_FOR_NEW_PASSWORD
    profile.save()


def process_restore_password(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['password'] = message.text
    prompt = utils.t(profile, "Yangi parolni tasdiqlang:", "Подтвердите новый пароль:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.RESET_WAITING_FOR_PASSWORD_CONFIRM
    profile.save()


def process_restore_password_confirm(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)

    if profile.temp_data.get('password') != message.text:
        bot.send_message(message.chat.id, utils.t(profile, "❌ Parollar mos kelmadi. Qaytadan urinib ko'ring.",
                                                  "❌ Пароли не совпадают. Попробуйте снова."))
        prompt = utils.t(profile, "Yangi parol yarating:", "Создайте новый пароль:")
        bot.send_message(message.chat.id, prompt)
        profile.step = UserSteps.RESET_WAITING_FOR_NEW_PASSWORD
        profile.save()
        return

    profile.temp_data['password_confirm'] = message.text
    response = api_client.restore_password(profile.language, profile.temp_data)

    if response and response.status_code == 200:
        success_msg = utils.t(profile, "✅ Parolingiz muvaffaqiyatli o'zgartirildi. Endi tizimga kirishingiz mumkin.",
                              "✅ Ваш пароль успешно изменен. Теперь вы можете войти в систему.")
        bot.send_message(message.chat.id, success_msg)
    else:
        error_msg = utils.t(profile, "Parolni tiklashda xatolik.", "Ошибка при восстановлении пароля.")
        if response is not None:
            try:
                error_msg = response.json().get('error', error_msg)
            except:
                pass
        bot.send_message(message.chat.id, f"❌ {error_msg}")

    profile.temp_data = {}
    profile.step = UserSteps.DEFAULT
    profile.save()
    show_profile_menu(message, bot)
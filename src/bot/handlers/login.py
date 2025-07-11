from ..models import TelegramProfile
from .. import utils, api_client
from ..constants import UserSteps
from .start import show_main_menu


def start_login(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    if profile.near_user_id:
        bot.send_message(message.chat.id, utils.t(profile, "Siz allaqachon tizimdasiz.", "Вы уже в системе."))
        return

    prompt = utils.t(profile, "Email manzilingizni kiriting:", "Введите ваш email:")
    bot.send_message(message.chat.id, prompt)

    profile.temp_data = {}
    profile.step = UserSteps.LOGIN_WAITING_FOR_EMAIL
    profile.save()


def process_login_email(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data = {'email': message.text}

    prompt = utils.t(profile, "Parolni kiriting:", "Введите пароль:")
    bot.send_message(message.chat.id, prompt)

    profile.step = UserSteps.LOGIN_WAITING_FOR_PASSWORD
    profile.save()


def process_login_password(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    email = profile.temp_data.get('email')
    password = message.text

    bot.send_message(message.chat.id, utils.t(profile, "Tekshirilmoqda...", "Проверка..."))

    is_success, response_message = api_client.login_and_link_profile(
        profile=profile,
        email=email,
        password=password
    )

    bot.send_message(message.chat.id, response_message)

    profile.temp_data = {}
    profile.step = UserSteps.DEFAULT
    profile.save()

    if is_success:
        show_main_menu(message, bot)

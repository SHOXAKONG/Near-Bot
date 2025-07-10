import jwt
import requests

from src.config import settings
from ..models import TelegramProfile
from .. import utils, keyboards, api_client
from ..constants import UserSteps
from .profile import show_profile_menu
from .start import show_main_menu


def start_registration(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    if profile.near_user_id:
        bot.send_message(message.chat.id, utils.t(profile, "Siz allaqachon tizimdasiz.", "Вы уже в системе."))
        return

    prompt = utils.t(profile, "Ismingizni kiriting:", "Введите ваше имя:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.REG_WAITING_FOR_FIRST_NAME
    profile.temp_data = {}
    profile.save()


def process_first_name(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['first_name'] = message.text
    prompt = utils.t(profile, "Familyangizni kiriting:", "Введите вашу фамилию:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.REG_WAITING_FOR_LAST_NAME
    profile.save()


def process_last_name(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['last_name'] = message.text
    prompt = utils.t(profile, "Email manzilingizni kiriting:", "Введите ваш email:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.REG_WAITING_FOR_EMAIL
    profile.save()


def process_email(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['email'] = message.text
    prompt = utils.t(profile, "Parol yarating:", "Создайте пароль:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.REG_WAITING_FOR_PASSWORD
    profile.save()


def process_password(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['password'] = message.text
    prompt = utils.t(profile, "Parolni tasdiqlang:", "Подтвердите пароль:")
    bot.send_message(message.chat.id, prompt)
    profile.step = UserSteps.REG_WAITING_FOR_PASSWORD_CONFIRM
    profile.save()


def process_password_confirm(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)

    if profile.temp_data.get('password') != message.text:
        bot.send_message(message.chat.id, utils.t(profile, "❌ Parollar mos kelmadi...", "❌ Пароли не совпадают..."))
        prompt = utils.t(profile, "Parol yarating:", "Создайте пароль:")
        bot.send_message(message.chat.id, prompt)
        profile.step = UserSteps.REG_WAITING_FOR_PASSWORD
        profile.save()
        return

    profile.temp_data['password_confirm'] = message.text

    bot.send_message(message.chat.id, utils.t(profile, "Ma'lumotlar yuborilmoqda...", "Отправляем данные..."))
    response = api_client.register_user(profile.language, profile.temp_data)

    if response and response.status_code == 201:
        prompt = utils.t(profile,
                         "✅ Ro‘yxatdan o‘tish muvaffaqiyatli! Hisobingizni faollashtirish uchun emailingizga yuborilgan tasdiqlash kodini kiriting:",
                         "✅ Регистрация прошла успешно! Введите код подтверждения, отправленный на вашу электронную почту, чтобы активировать свою учетную запись:")
        bot.send_message(message.chat.id, prompt)
        profile.step = UserSteps.REG_WAITING_FOR_CONFIRMATION_CODE
    else:
        error_msg = utils.t(profile, "Noma'lum xatolik.", "Неизвестная ошибка.")
        if response is not None:
            try:
                error_data = response.json()
                error_msg = next(iter(error_data.values()))[0] if isinstance(next(iter(error_data.values())), list) else next(iter(error_data.values()))
            except (requests.exceptions.JSONDecodeError, AttributeError):
                error_msg = f"Server xatosi (kod: {response.status_code})."

        bot.send_message(message.chat.id, f"❌ Ro'yxatdan o'tishda xatolik: {error_msg}")
        profile.step = UserSteps.DEFAULT
        show_profile_menu(message, bot)

    profile.save()


def process_confirmation_code(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    code = message.text

    response = api_client.confirm_registration(profile.language, code)

    if response and response.ok:
        try:
            api_data = response.json()
            access = api_data.get('access')
            refresh = api_data.get('refresh')

            if not (access and refresh):
                bot.send_message(message.chat.id,
                                 "❌ Hisob faollashtirildi, lekin avtomatik kirishda xatolik yuz berdi (API token qaytarmadi).")
                show_profile_menu(message, bot)
            else:
                try:
                    decoded_data = jwt.decode(access, options={"verify_signature": False})
                    user_id = decoded_data.get('user_id')

                    if not user_id:
                        raise ValueError("Token tarkibida user_id topilmadi.")

                    profile.near_user_id = user_id
                    profile.access_token = access
                    profile.refresh_token = refresh
                    profile.save()

                    success_message = utils.t(profile, "✅ Hisobingiz faollashtirildi va siz tizimga kirdingiz!",
                                              "✅ Ваш аккаунт активирован и вы вошли в систему!")
                    bot.send_message(message.chat.id, success_message)
                    show_main_menu(message, bot)

                except (jwt.DecodeError, ValueError) as e:
                    print(f"Tokenni ochishda xatolik: {e}")
                    bot.send_message(message.chat.id, "❌ Tizimga kirishda ichki xatolik yuz berdi.")
                    show_profile_menu(message, bot)

        except requests.exceptions.JSONDecodeError:
            bot.send_message(message.chat.id, "❌ Serverdan kutilmagan javob keldi.")
            show_profile_menu(message, bot)
    else:
        error_message = utils.t(profile, 'Kod xato yoki eskirgan.', 'Код неверный или просрочен.')
        if response is not None:
            try:
                error_message = response.json().get('error', error_message)
            except:
                pass
        bot.send_message(message.chat.id, f"❌ {error_message}")
        show_profile_menu(message, bot)

    profile.temp_data = {}
    profile.step = UserSteps.DEFAULT
    profile.save()
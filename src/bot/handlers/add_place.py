import json

import requests
import telebot
import os
import tempfile

from src.config import settings
from ..models import TelegramProfile
from .. import utils, keyboards, api_client
from ..constants import UserSteps
from .start import show_main_menu
from ..utils import convert_image


def start_add_place(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    if not profile.near_user_id:
        bot.send_message(message.chat.id, utils.t(profile, "Bu funksiyadan foydalanish uchun avval tizimga kiring.",
                                                  "Для использования этой функции, пожалуйста, войдите в систему."))
        return

    response = api_client.get_user_data_from_api(profile)

    if response and response.status_code == 200:
        user_data = response.json()
        if user_data.get('role') == 'entrepreneur':
            prompt = utils.t(profile, "Yangi joy qo'shish boshlandi.\n\nJoy nomini kiriting (O'zbekcha):",
                             "Начато добавление нового места.\n\nВведите название места (Узбекский):")
            bot.send_message(message.chat.id, prompt)
            profile.step = UserSteps.PLACE_ADD_WAITING_FOR_NAME_UZ
            profile.temp_data = {}
            profile.save()
        else:
            bot.send_message(message.chat.id, utils.t(profile, "Bu funksiya faqat tasdiqlangan tadbirkorlar uchun.",
                                                      "Эта функция только для подтвержденных предпринимателей."))
    else:
        bot.send_message(message.chat.id, utils.t(profile, "Foydalanuvchi ma'lumotlarini olib bo'lmadi.",
                                                  "Не удалось получить данные пользователя."))
        show_main_menu(message, bot)


def process_place_name_uz(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['name_uz'] = message.text
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_NAME_RU
    profile.save()
    prompt = utils.t(profile, "Joy nomini kiriting (Ruscha):", "Введите название места (Русский):")
    bot.send_message(message.chat.id, prompt)


def process_place_name_ru(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['name_ru'] = message.text
    response = api_client.get_categories(profile)
    if response and response.status_code == 200:
        categories = response.json()
        profile.temp_data['all_categories'] = categories
        profile.step = UserSteps.PLACE_ADD_WAITING_FOR_CATEGORY
        profile.save()
        markup = keyboards.get_category_keyboard(profile, categories)
        prompt = utils.t(profile, "Joy kategoriyasini tanlang:", "Выберите категорию места:")
        bot.send_message(message.chat.id, prompt, reply_markup=markup)
    else:
        bot.send_message(message.chat.id,
                         utils.t(profile, "Kategoriyalarni yuklab bo'lmadi.", "Не удалось загрузить категории."))
        show_main_menu(message, bot)


def process_place_category(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    category_name = message.text
    category_id = next(
        (cat['id'] for cat in profile.temp_data.get('all_categories', []) if cat['name'] == category_name), None)
    if not category_id:
        bot.send_message(message.chat.id, utils.t(profile, "Iltimos, pastdagi tugmalardan birini tanlang.",
                                                  "Пожалуйста, выберите одну из кнопок ниже."))
        return
    profile.temp_data['category'] = category_id
    profile.temp_data['category_name'] = category_name
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_LOCATION
    profile.save()
    prompt = utils.t(profile, "Joylashuvni xaritadan belgilab yuboring:", "Отправьте геолокацию места:")
    markup = keyboards.get_location_request_keyboard(profile)
    bot.send_message(message.chat.id, prompt, reply_markup=markup)


def process_place_location(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    if not message.location:
        bot.send_message(message.chat.id, utils.t(profile, "Iltimos, lokatsiyani tugma orqali yuboring.",
                                                  "Пожалуйста, отправьте геолокацию с помощью кнопки."))
        return
    profile.temp_data['latitude'] = message.location.latitude
    profile.temp_data['longitude'] = message.location.longitude
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_CONTACT
    profile.save()
    prompt = utils.t(profile, "Bog'lanish uchun ma'lumot kiriting (telefon raqam):",
                     "Введите контактную информацию (номер телефона):")
    bot.send_message(message.chat.id, prompt, reply_markup=telebot.types.ReplyKeyboardRemove())


def process_place_contact(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['contact'] = message.text
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_DESCRIPTION_UZ
    profile.save()
    prompt = utils.t(profile, "Joy haqida qisqacha tavsif yozing (O'zbekcha):",
                     "Напишите краткое описание места (Узбекский):")
    bot.send_message(message.chat.id, prompt)


def process_place_description_uz(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['description_uz'] = message.text
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_DESCRIPTION_RU
    profile.save()
    prompt = utils.t(profile, "Joy haqida qisqacha tavsif yozing (Ruscha):",
                     "Напишите краткое описание места (Русский):")
    bot.send_message(message.chat.id, prompt)


def process_place_description_ru(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    profile.temp_data['description_ru'] = message.text
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_IMAGE
    profile.save()
    prompt = utils.t(profile, "Joyning asosiy rasmini yuboring:", "Отправьте главное фото места:")
    bot.send_message(message.chat.id, prompt)


def process_place_image(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    if not message.photo:
        bot.send_message(message.chat.id,
                         utils.t(profile, "Iltimos, faqat rasm yuboring.", "Пожалуйста, отправьте только фото."))
        return

    bot.send_message(message.chat.id, utils.t(profile, "Rasm yuklanmoqda va qayta ishlanmoqda...",
                                              "Фото загружается и обрабатывается..."))
    file_id = message.photo[-1].file_id
    try:
        file_info_url = "https://api.telegram.org/bot{token}/getFile?file_id={file_id}".format(token=settings.BOT_TOKEN,
                                                                                               file_id=file_id)
        file_info_res = requests.get(file_info_url)
        file_info_res.raise_for_status()
        file_path = file_info_res.json()['result']['file_path']
        file_url = "https://api.telegram.org/file/bot{token}/{file_path}".format(token=settings.BOT_TOKEN,
                                                                                 file_path=file_path)
        image_res = requests.get(file_url)
        image_res.raise_for_status()
        converted_image_bytes = convert_image(image_res.content, target_format='JPEG')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(converted_image_bytes)
        temp_file.close()
        profile.temp_data['image_path'] = temp_file.name
        _show_confirmation_message(message, bot, profile)
    except Exception as e:
        print("Rasm bilan ishlashda xatolik: {}".format(e))
        bot.send_message(message.chat.id, utils.t(profile,
                                                  "❌ Rasmni yuklashda xatolik yuz berdi. Iltimos, boshqa rasm yuboring yoki jarayonni bekor qiling.",
                                                  "❌ Произошла ошибка при загрузке фото. Пожалуйста, отправьте другое фото или отмените процесс."))


def _show_confirmation_message(message, bot, profile):
    data = profile.temp_data
    image_path = data.get('image_path')
    if not image_path:
        bot.send_message(message.chat.id, "Tasdiqlash uchun rasm topilmadi.")
        return

    confirmation_text = "<b>{title}</b>\n\n".format(
        title=utils.t(profile, 'Iltimos, ma\'lumotlarni tekshiring:', 'Пожалуйста, проверьте данные:'))
    confirmation_text += "<b>{label}:</b> {value}\n".format(label=utils.t(profile, 'Nomi (UZ)', 'Название (УЗ)'),
                                                            value=data.get('name_uz', ''))
    confirmation_text += "<b>{label}:</b> {value}\n".format(label=utils.t(profile, 'Nomi (RU)', 'Название (РУ)'),
                                                            value=data.get('name_ru', ''))
    confirmation_text += "<b>{label}:</b> {value}\n".format(label=utils.t(profile, 'Kategoriya', 'Категория'),
                                                            value=data.get('category_name', ''))
    confirmation_text += "<b>{label}:</b> Lat: {lat}, Lon: {lon}\n".format(
        label=utils.t(profile, 'Lokatsiya', 'Локация'), lat=data.get('latitude', ''), lon=data.get('longitude', ''))
    confirmation_text += "<b>{label}:</b> {value}\n".format(label=utils.t(profile, 'Kontakt', 'Контакт'),
                                                            value=data.get('contact', ''))
    confirmation_text += "<b>{label}:</b> {value}\n".format(label=utils.t(profile, 'Tavsif (UZ)', 'Описание (УЗ)'),
                                                            value=data.get('description_uz', ''))
    confirmation_text += "<b>{label}:</b> {value}".format(label=utils.t(profile, 'Tavsif (RU)', 'Описание (РУ)'),
                                                          value=data.get('description_ru', ''))

    markup = keyboards.get_add_place_confirmation_keyboard(profile)
    with open(image_path, 'rb') as photo_to_send:
        bot.send_photo(message.chat.id, photo_to_send, caption=confirmation_text, reply_markup=markup,
                       parse_mode='HTML')
    profile.step = UserSteps.PLACE_ADD_WAITING_FOR_CONFIRMATION
    profile.save()


def process_add_place_confirm(call, bot):
    profile = TelegramProfile.objects.get(tg_id=call.message.chat.id)
    if not profile.near_user_id:
        bot.answer_callback_query(call.id, "Xatolik: Foydalanuvchi topilmadi.", show_alert=True)
        return

    lang = profile.language

    data_to_send = {
        "name": profile.temp_data.get(f"name_{lang}"),
        "name_uz": profile.temp_data.get("name_uz"),
        "name_ru": profile.temp_data.get("name_ru"),
        "description": profile.temp_data.get(f"description_{lang}"),
        "description_uz": profile.temp_data.get("description_uz"),
        "description_ru": profile.temp_data.get("description_ru"),
        "category": profile.temp_data.get("category"),
        "location": json.dumps({
            "latitude": profile.temp_data.get("latitude"),
            "longitude": profile.temp_data.get("longitude")
        }) if profile.temp_data.get("latitude") and profile.temp_data.get("longitude") else None,
        "contact": profile.temp_data.get("contact"),
        "image_path": profile.temp_data.get("image_path") if profile.temp_data.get("image_path") else None,
    }

    response = api_client.add_place(profile, data_to_send)
    bot.delete_message(call.message.chat.id, call.message.message_id)

    if response and response.status_code == 201:
        bot.send_message(call.message.chat.id,
                         utils.t(profile, "✅ Joy muvaffaqiyatli qo'shildi!", "✅ Место успешно добавлено!"))
    else:
        error_details = "Noma'lum server xatoligi."
        if response is not None:
            try:
                error_data = response.json()
                formatted_errors = []
                for field, messages in error_data.items():
                    msg = messages[0] if isinstance(messages, list) else messages
                    formatted_errors.append("`{}`: {}".format(field, msg))
                error_details = "\n".join(formatted_errors)
            except:
                error_details = response.text

        error_title = utils.t(profile, "❌ Joy qo'shishda xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring",
                              "❌ Произошла ошибка при добавлении места. Пожалуйста, проверьте данные")
        final_error_message = "{}:\n\n{}".format(error_title, error_details)
        bot.send_message(call.message.chat.id, final_error_message, parse_mode="Markdown")

    profile.temp_data = {}
    profile.step = UserSteps.DEFAULT
    profile.save()
    show_main_menu(call.message, bot)


def process_add_place_cancel(call, bot):
    profile = TelegramProfile.objects.get(tg_id=call.message.chat.id)
    image_path = profile.temp_data.get('image_path')
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
            print(f"Canceled. Temporary file {image_path} deleted.")
        except OSError as e:
            print(f"Error deleting temporary file on cancel: {e}")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.message.chat.id,
                     utils.t(profile, "❌ Joy qo'shish bekor qilindi.", "❌ Добавление места отменено."))
    profile.temp_data = {}
    profile.step = UserSteps.DEFAULT
    profile.save()
    show_main_menu(call.message, bot)

from io import BytesIO

import requests
import telebot
from ..models import TelegramProfile
from .. import utils, keyboards, api_client
from ..constants import UserSteps
from .start import show_main_menu


def start_search_by_location(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)

    profile.temp_data = {
        'latitude': message.location.latitude,
        'longitude': message.location.longitude
    }

    response = api_client.get_categories(profile)
    if response and response.status_code == 200:
        categories = response.json()
        if not categories:
            bot.send_message(message.chat.id,
                             utils.t(profile, "Hozircha kategoriyalar mavjud emas.", "Категории пока недоступны."))
            return

        profile.temp_data['categories'] = categories
        profile.step = UserSteps.SEARCH_WAITING_FOR_CATEGORY
        profile.save()

        markup = keyboards.get_category_keyboard(profile, categories)
        prompt = utils.t(profile, "Joylashuv qabul qilindi. Endi kerakli kategoriyani tanlang:",
                         "Местоположение получено. Теперь выберите нужную категорию:")
        bot.send_message(message.chat.id, prompt, reply_markup=markup)
    else:
        bot.send_message(message.chat.id,
                         utils.t(profile, "Kategoriyalarni yuklashda xatolik.", "Ошибка при загрузке категорий."))
        show_main_menu(message, bot)


def start_category_search(message, bot):
    profile, _ = TelegramProfile.objects.get_or_create(tg_id=message.chat.id)
    response = api_client.get_categories(profile)

    if response and response.status_code == 200:
        data = response.json()
        categories = data.get("results", [])  # ✅ faqat resultsni olish
        print(categories)

        if not categories:
            bot.send_message(
                message.chat.id,
                utils.t(profile, "Hozircha kategoriyalar mavjud emas.", "Категории пока недоступны.")
            )
            return

        profile.temp_data = {'categories': categories}
        profile.step = UserSteps.SEARCH_WAITING_FOR_CATEGORY
        profile.save()

        markup = keyboards.get_category_keyboard(profile, categories)
        bot.send_message(
            message.chat.id,
            utils.t(profile, "Kategoriyani tanlang:", "Выберите категорию:"),
            reply_markup=markup
        )
    else:
        bot.send_message(
            message.chat.id,
            utils.t(profile, "Kategoriyalarni yuklashda xatolik.", "Ошибка при загрузке категорий.")
        )



def process_category_selection(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    selected_name = message.text

    back_to_menu_text = utils.t(profile, '⬅️ Bosh menyu', '⬅️ Главное меню')
    if selected_name == back_to_menu_text:
        show_main_menu(message, bot)
        return

    all_categories = profile.temp_data.get('categories', [])
    category_id = next((cat['id'] for cat in all_categories if cat['name'] == selected_name), None)

    if category_id:
        profile.temp_data['category_id'] = category_id

        if profile.temp_data.get('latitude') and profile.temp_data.get('longitude'):
            bot.send_message(message.chat.id, utils.t(profile, "Qidirilmoqda...", "Идёт поиск..."),
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            _perform_search(message, bot, profile)
        else:
            prompt = utils.t(profile, "Eng yaqin joylarni topish uchun joylashuvingizni yuboring.",
                             "Отправьте вашу геолокацию...")
            markup = keyboards.get_location_request_keyboard(profile)
            bot.send_message(message.chat.id, prompt, reply_markup=markup)
            profile.step = UserSteps.SEARCH_WAITING_FOR_LOCATION
    else:
        bot.send_message(message.chat.id, utils.t(profile, "Iltimos, pastdagi tugmalardan birini tanlang.",
                                                  "Пожалуйста, выберите одну из кнопок ниже."))

    profile.save()


def process_location_step(message, bot):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)

    if message.text and (message.text in ["❌ Bekor qilish", "❌ Отмена"]):
        show_main_menu(message, bot)
        return

    if not message.location:
        bot.send_message(message.chat.id, utils.t(profile, "Iltimos, joylashuvingizni pastdagi tugma orqali yuboring.",
                                                  "Пожалуйста, отправьте вашу геолокацию с помощью кнопки внизу."))
        return

    lat = message.location.latitude
    lon = message.location.longitude
    profile.temp_data['latitude'] = lat
    profile.temp_data['longitude'] = lon
    profile.save()

    searching_msg = bot.send_message(
        message.chat.id,
        utils.t(profile, "Qidirilmoqda...", "Идёт поиск..."),
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )

    bot.delete_message(message.chat.id, searching_msg.message_id)
    _perform_search(message, bot, profile)


def _perform_search(message, bot, profile):
    category_id = profile.temp_data.get('category_id')
    lat = profile.temp_data.get('latitude')
    lon = profile.temp_data.get('longitude')

    if not all([category_id, lat, lon]):
        bot.send_message(message.chat.id, "Qidiruv uchun ma'lumotlar to'liq emas.")
        show_main_menu(message, bot)
        return

    response = api_client.search_places(profile, lat, lon, int(category_id))

    if response and response.status_code == 200:
        places = response.json().get('results', [])
        if not places:
            bot.send_message(message.chat.id,
                             utils.t(profile, "Afsuski, bu kategoriya bo'yicha yaqin atrofda hech narsa topilmadi.",
                                     "К сожалению, поблизости ничего не найдено по этой категории."))
            show_main_menu(message, bot)
        else:
            api_client.log_search_activity(profile, category_id, lat, lon)

            profile.temp_data['places'] = places
            profile.save()
            show_paginated_place(message, bot, index=0)

    else:
        bot.send_message(message.chat.id,
                         utils.t(profile, "Qidirishda xatolik yuz berdi.", "Произошла ошибка при поиске."))
        show_main_menu(message, bot)


def show_paginated_place(message, bot, index=0):
    profile = TelegramProfile.objects.get(tg_id=message.chat.id)
    places = profile.temp_data.get('places', [])

    if not places or not (0 <= index < len(places)):
        return

    place = places[index]
    lang = profile.language

    # Place name (fallback if missing)
    name = place.get(f'name_{lang}') or place.get('name_ru') or place.get('name_uz') or "Nomsiz / Без названия"

    # Description (fallback if missing)
    description = place.get(f'description_{lang}') or place.get('description_ru') or place.get('description_uz') or place.get('description') or ""

    contact = place.get('contact', '')
    distance = place.get('distance')

    # Build caption
    MAX_CAPTION_LENGTH = 1024
    caption = f"<b>{name}</b>\n\n"

    if distance is not None:
        caption += f"📍 {utils.t(profile, 'Masofa', 'Расстояние')}: {distance:.2f} km\n\n"

    if contact:
        caption += f"📞 {utils.t(profile, 'Kontakt', 'Контакт')}: {contact}\n\n"

    available_len = MAX_CAPTION_LENGTH - len(caption) - 5
    if len(description) > available_len:
        description = description[:available_len] + "..."
    caption += description

    # Pagination keyboard
    markup = keyboards.get_place_pagination_keyboard(profile, index, len(places), place)

    # ✅ Use image directly from API
    image_url = place.get("image_url")
    print("Image from API:", image_url)

    if image_url:
        try:
            # fetch image and send as file (ensures Telegram always accepts it)
            r = requests.get(image_url, timeout=10)
            r.raise_for_status()
            bio = BytesIO(r.content)
            bio.name = "photo.png"  # Telegram requires filename
            bot.send_photo(
                message.chat.id,
                photo=bio,
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception as e:
            print(f"Telegram photo error: {e}")
            bot.send_message(message.chat.id, caption, parse_mode="HTML", reply_markup=markup)
    else:
        bot.send_message(message.chat.id, caption, parse_mode="HTML", reply_markup=markup)



def show_paginated_place_callback(call, bot):
    profile = TelegramProfile.objects.get(tg_id=call.message.chat.id)
    index = int(call.data.split('_')[1])

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Could not delete message for pagination: {e}")

    show_paginated_place(call.message, bot, index=index)


def handle_reshow_categories(call, bot):
    profile = TelegramProfile.objects.get(tg_id=call.message.chat.id)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Could not delete message, but proceeding. Error: {e}")

    response = api_client.get_categories(profile)

    if response and response.status_code == 200:
        data = response.json()
        categories = data.get("results", [])

        if not categories:
            bot.send_message(
                call.message.chat.id,
                utils.t(profile, "Hozircha kategoriyalar mavjud emas.", "Категории пока недоступны.")
            )
            from .start import show_main_menu
            show_main_menu(call.message, bot)
            return

        profile.temp_data['categories'] = categories
        profile.step = UserSteps.SEARCH_WAITING_FOR_CATEGORY
        profile.save()

        markup = keyboards.get_category_keyboard(profile, categories)
        bot.send_message(
            call.message.chat.id,
            utils.t(profile, "Boshqa kategoriyani tanlang:", "Выберите другую категорию:"),
            reply_markup=markup
        )
    else:
        bot.send_message(
            call.message.chat.id,
            utils.t(profile, "Kategoriyalarni yuklashda xatolik.", "Ошибка при загрузке категорий.")
        )
        from .start import show_main_menu
        show_main_menu(call.message, bot)


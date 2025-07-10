import os

import jwt
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.conf import settings
from .models import TelegramProfile


def refresh_access_token(profile: TelegramProfile):
    if not profile.refresh_token:
        return None

    url = f"{settings.BASE_URL}/{profile.language}/api/auth/login-token/refresh/"
    try:
        response = requests.post(url, json={'refresh': profile.refresh_token})
        if response.status_code == 200:
            new_access_token = response.json().get('access')
            profile.access_token = new_access_token
            profile.save(update_fields=['access_token'])
            return new_access_token
        else:
            profile.near_user_id = None
            profile.access_token = None
            profile.refresh_token = None
            profile.save()
            return None
    except requests.RequestException:
        return None


def make_authenticated_request(profile: TelegramProfile, method: str, url: str, **kwargs):
    if not profile.access_token:
        print("Xatolik: So'rov uchun access token topilmadi.")
        return None

    headers = kwargs.setdefault('headers', {})
    headers['Authorization'] = f'Bearer {profile.access_token}'

    session = requests.Session()
    retries = Retry(total=3, backoff_factor=0.2, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    response = session.request(method, url, **kwargs)

    if response.status_code == 401:
        print("Access token yaroqsiz. Yangilanmoqda...")
        new_token = refresh_access_token(profile)
        if new_token:
            print("Token muvaffaqiyatli yangilandi. So'rov qayta yuborilmoqda.")
            headers['Authorization'] = f'Bearer {new_token}'
            response = session.request(method, url, **kwargs)
        else:
            print("Tokenni yangilab bo'lmadi.")

    return response


def login_and_link_profile(telegram_id: int, email: str, password: str, profile: TelegramProfile):
    LOGIN_URL = f"{settings.BASE_URL}/{profile.language}/api/auth/login/"

    try:
        login_response = requests.post(LOGIN_URL, json={'email': email, 'password': password})
        if login_response.status_code != 200:
            return (False, "Login yoki parol xato.")

        tokens = login_response.json()
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')

        if not access_token:
            return (False, "API javobida token topilmadi.")

        try:
            decoded_data = jwt.decode(access_token, options={"verify_signature": False})
            near_user_id = decoded_data.get('user_id')

            if not near_user_id:
                raise ValueError("Token tarkibida user_id topilmadi.")

        except (jwt.DecodeError, ValueError) as e:
            print(f"Tokenni ochishda xatolik: {e}")
            return (False, "Tizimga kirishda ichki xatolik yuz berdi.")

        profile.near_user_id = near_user_id
        profile.access_token = access_token
        profile.refresh_token = refresh_token
        profile.save()
        return (True, "Muvaffaqiyatli! Profilingiz tizimga bog'landi.")

    except requests.exceptions.RequestException as e:
        return (False, f"API bilan bog'lanishda xatolik: {e}")
    except Exception as e:
        return (False, f"Profilni saqlashda noma'lum xatolik: {e}")


def register_user(lang: str, data: dict):
    url = f"{settings.BASE_URL}/{lang}/api/auth/register/"
    return requests.post(url, json=data)


def confirm_registration(lang: str, code: str):
    url = f"{settings.BASE_URL}/{lang}/api/auth/confirm/"
    return requests.post(url, json={"code": code})


def forgot_password(lang: str, email: str):
    url = f"{settings.BASE_URL}/{lang}/api/auth/forgot_password/"
    return requests.post(url, json={'email': email})


def restore_password(lang: str, data: dict):
    url = f"{settings.BASE_URL}/{lang}/api/auth/restore_password/"
    return requests.post(url, json=data)


def get_user_data_from_api(profile: TelegramProfile):
    if not profile.near_user_id:
        return None

    user_id = profile.near_user_id
    print(profile)
    print(user_id)
    url = f"{settings.BASE_URL}/{profile.language}/api/auth/users-data/{user_id}/"
    return make_authenticated_request(profile, 'get', url)


def add_place(profile: TelegramProfile, place_data: dict):
    url = f"{settings.BASE_URL}/{profile.language}/api/place/"
    image_path = place_data.pop('image_path', None)
    files_to_upload = {}
    file_handle = None
    try:
        if image_path and os.path.exists(image_path):
            file_handle = open(image_path, 'rb')
            files_to_upload['image'] = (os.path.basename(image_path), file_handle, 'image/jpeg')
        return make_authenticated_request(profile, 'post', url, data=place_data, files=files_to_upload, timeout=25)
    except requests.RequestException as e:
        print(f"Joy qo'shishda xatolik: {e}")
        return None
    finally:
        if file_handle:
            file_handle.close()
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
            except OSError as e:
                print(f"Vaqtinchalik faylni o'chirishda xatolik {image_path}: {e}")


def become_entrepreneur(profile: TelegramProfile):
    url = f"{settings.BASE_URL}/{profile.language}/api/auth/become-entrepreneur/"
    return make_authenticated_request(profile, 'post', url)


def log_search_activity(profile: TelegramProfile, category_id: int):
    if not profile.near_user_id:
        return None
    url = f"{settings.BASE_URL}/{profile.language}/api/search-history/"
    data = {'category': category_id}
    return make_authenticated_request(profile, 'post', url, json=data)


def get_categories(profile: TelegramProfile):
    url = f"{settings.BASE_URL}/{profile.language}/api/category/"
    try:
        return requests.get(url, timeout=10)
    except requests.RequestException as e:
        print(f"Kategoriyalarni olishda xatolik: {e}")
        return None


def search_places(profile: TelegramProfile, lat: float, lon: float, category_id: int):
    url = f"{settings.BASE_URL}/{profile.language}/api/place/"
    params = {'latitude': lat, 'longitude': lon, 'category': category_id}
    try:
        return requests.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        print(f"Joylarni qidirishda xatolik: {e}")
        return None

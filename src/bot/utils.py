import json
import base64

from PIL import Image
import io

def t(profile, key_uz: str, key_ru: str) -> str:
    return key_uz if profile.language == 'uz' else key_ru

def decode_token(token: str) -> dict:
    try:
        payload_b64 = token.split('.')[1]
        payload_b64 += '=' * (-len(payload_b64) % 4)
        payload_json = base64.b64decode(payload_b64).decode('utf-8')
        return json.loads(payload_json)
    except Exception:
        return {}


def convert_image(image_bytes: bytes, target_format: str = 'JPEG', quality: int = 85, size: int = 300) -> bytes:
    try:
        image = Image.open(io.BytesIO(image_bytes))

        width, height = image.size
        min_dim = min(width, height)
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2
        image = image.crop((left, top, right, bottom))

        image = image.resize((size, size), Image.ANTIALIAS)

        if target_format.upper() == 'JPEG' and image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')

        output_buffer = io.BytesIO()
        image.save(output_buffer, format=target_format.upper(), quality=quality, optimize=True)

        return output_buffer.getvalue()

    except Exception as e:
        print(f"[convert_image] Error processing image: {e}")
        return image_bytes

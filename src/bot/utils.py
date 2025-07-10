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


def convert_image(image_bytes: bytes, target_format: str = 'JPEG', quality: int = 85) -> bytes:

    try:
        image = Image.open(io.BytesIO(image_bytes))

        output_buffer = io.BytesIO()

        if target_format.upper() == 'JPEG':
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')

            image.save(output_buffer, format='JPEG', quality=quality, optimize=True)

        elif target_format.upper() == 'PNG':
            image.save(output_buffer, format='PNG', optimize=True)

        else:
            raise ValueError("Qo'llab-quvvatlanadigan formatlar: 'JPEG' yoki 'PNG'")

        converted_bytes = output_buffer.getvalue()
        return converted_bytes

    except Exception as e:
        return image_bytes
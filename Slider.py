
# الترخيص: @TopVeGa
# العلامة التجارية: VEGA & لوجيك | Logic™
# حقوق الطبع والنشر: © 2015 - 2025


import os
import io
import time
import asyncio
import aiohttp
from pyrogram import Client, filters, enums
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto,
)
from PIL import Image, ImageDraw



# لوجيك | Logic وجهتك البرمجية الأولى  بالوطن العربي
# شروحات - أكواد - وأحدث تقنيات برمجية - وحلول تقنية
# بواسطه: @Logii3



API_ID = int(os.getenv("API_ID", " "))
API_HASH = os.getenv("API_HASH", " ")
BOT_TOKEN = os.getenv("BOT_TOKEN", " ")

ParseMode = enums.ParseMode
app = Client("TopVeGa", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

_USE_RICH_MESSAGE = True
_RICH_TIMEOUT = 60

user_photos_cache = {}
_PHOTOS_TTL = 300


def safe_mention(user) -> str:
    first_name = getattr(user, "first_name", None) or "مستخدم"
    return f'<a href="tg://user?id={user.id}">{first_name}</a>'


def extract_file_id(obj):
    if obj is None:
        return None
    for attr in ("file_id", "big_file_id", "small_file_id"):
        fid = getattr(obj, attr, None)
        if fid:
            return fid
    return None


async def _fetch_user_photos(client, user_id, limit=10):
    photos = []
    try:
        async for photo in client.get_chat_photos(user_id, limit=limit):
            fid = extract_file_id(photo)
            if fid and fid not in photos:
                photos.append(fid)
    except Exception as e:
        print(f"[_fetch_user_photos] {e}")
    return photos


def draw_dots_on_image(image_bytes: bytes, total: int, current: int) -> bytes:
    if total <= 1:
        return image_bytes
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        width, height = img.size
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        base_size = width // 100
        dot_radius = max(5, min(base_size, 12))
        inactive_radius = max(4, dot_radius - 2)
        dot_spacing = dot_radius * 4

        active_color = (255, 255, 255, 255)
        inactive_color = (255, 255, 255, 110)
        shadow_color = (0, 0, 0, 100)

        total_width = (total - 1) * dot_spacing
        start_x = (width - total_width) // 2
        center_y = height - (dot_radius * 4)

        for i in range(total):
            cx = start_x + (i * dot_spacing)
            cy = center_y
            if i == current:
                draw.ellipse(
                    [cx - dot_radius - 2, cy - dot_radius - 2,
                     cx + dot_radius + 2, cy + dot_radius + 2],
                    fill=shadow_color,
                )
                draw.ellipse(
                    [cx - dot_radius, cy - dot_radius,
                     cx + dot_radius, cy + dot_radius],
                    fill=active_color,
                )
            else:
                draw.ellipse(
                    [cx - inactive_radius - 1, cy - inactive_radius - 1,
                     cx + inactive_radius + 1, cy + inactive_radius + 1],
                    fill=shadow_color,
                )
                draw.ellipse(
                    [cx - inactive_radius, cy - inactive_radius,
                     cx + inactive_radius, cy + inactive_radius],
                    fill=inactive_color,
                )

        combined = Image.alpha_composite(img, overlay)
        final = Image.new("RGB", combined.size, (255, 255, 255))
        final.paste(combined, mask=combined.split()[3])
        output = io.BytesIO()
        final.save(output, format="JPEG", quality=92, optimize=True)
        output.seek(0)
        return output.getvalue()
    except Exception as e:
        print(f"خطأ في رسم النقاط: {e}")
        return image_bytes


async def send_rich_slideshow(
    chat_id: int,
    photo_file_ids: list[str],
    caption: str = "",
    buttons: list[dict] | None = None,
) -> dict | None:
    global _USE_RICH_MESSAGE

    if not _USE_RICH_MESSAGE:
        return None
    if not photo_file_ids or len(photo_file_ids) < 2:
        return None

    photos = photo_file_ids[:10]

    media_payload = []
    slideshow_tags = ""
    for i, fid in enumerate(photos):
        mid = f"p{i}"
        media_payload.append({
            "id": mid,
            "media": {"type": "photo", "media": fid},
        })
        slideshow_tags += f'<img src="tg://photo?id={mid}"/>'

    rich_html = f"<tg-slideshow>{slideshow_tags}</tg-slideshow>"

    if caption:
        caption_html = caption.replace("\n", "<br/>")
        rich_html += f"<br/>{caption_html}"

    if buttons:
        btn_tags = ""
        for b in buttons:
            emoji_attr = (
                f' icon_custom_emoji_id="{b["emoji_id"]}"'
                if b.get("emoji_id") else ""
            )
            style = b.get("style", "primary")
            if b.get("url"):
                btn_tags += (
                    f'<tg-button url="{b["url"]}" style="{style}"{emoji_attr}>'
                    f'{b["text"]}'
                    f'</tg-button>'
                )
        if btn_tags:
            rich_html += f'<tg-button-row align="center">{btn_tags}</tg-button-row>'

    payload = {
        "chat_id": chat_id,
        "rich_message": {
            "html": rich_html,
            "media": media_payload,
        },
    }

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendRichMessage"

    try:
        timeout = aiohttp.ClientTimeout(
            total=_RICH_TIMEOUT, connect=15, sock_read=_RICH_TIMEOUT
        )
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as resp:
                text = await resp.text()
                try:
                    data = await resp.json(content_type=None)
                except Exception:
                    print(f"[rich] response not JSON: {text[:200]}")
                    return None

                if data.get("ok"):
                    print(f"[rich]  Sent to {chat_id}")
                    return data["result"]

                err_code = data.get("error_code")
                err_desc = data.get("description", "")
                print(f"[rich]  API {err_code}: {err_desc}")

                if err_code in (400, 404, 405):
                    _USE_RICH_MESSAGE = False
                    print("[rich]  sendRichMessage not supported → album mode")
                    return None

                return None
    except asyncio.TimeoutError:
        print(f"[rich] ⏱️ Timeout for {chat_id}")
        _USE_RICH_MESSAGE = False
        return None
    except Exception as e:
        print(f"[rich]  {e}")
        return None


def build_id_keyboard(user_id: int, user_name: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(user_name, url=f"tg://user?id={user_id}")]
    ])


async def send_id_card(client, message, user_id, base_text, user_name):
    now = time.time()
    cached = user_photos_cache.get(user_id)
    if cached and (now - cached[0]) < _PHOTOS_TTL:
        photos = cached[1]
    else:
        photos = await _fetch_user_photos(client, user_id, limit=10)
        user_photos_cache[user_id] = (now, photos)

    kb = build_id_keyboard(user_id, user_name)

    if len(photos) >= 2 and _USE_RICH_MESSAGE:
        try:
            res = await send_rich_slideshow(
                chat_id=message.chat.id,
                photo_file_ids=photos,
                caption=base_text,
                buttons=[{
                    "text": user_name,
                    "url": f"tg://user?id={user_id}",
                    "style": "primary",
                }],
            )
            if res:
                return res
            print(f"[rich]  فشل السلايدر — تحويل للألبوم")
        except Exception as e:
            print(f"[rich]  {e}")

    if len(photos) >= 2:
        try:
            media_list = []
            for i, fid in enumerate(photos[:10]):
                media_list.append(
                    InputMediaPhoto(
                        fid,
                        caption=base_text if i == 0 else None,
                        parse_mode=ParseMode.HTML,
                    )
                )
            msgs = await message.reply_media_group(media=media_list)
            await message.reply_text("•", reply_markup=kb)
            return {"message_id": msgs[0].id}
        except Exception as e:
            print(f"[album]  {e}")

    if len(photos) == 1:
        try:
            return await message.reply_photo(
                photo=photos[0],
                caption=base_text,
                reply_markup=kb,
                parse_mode=ParseMode.HTML,
            )
        except Exception as e:
            print(f"[photo]  {e}")

    return await message.reply_text(
        base_text,
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@app.on_message(
    filters.command(["ايدي", "الايدي", "ا", "id", "/id", "/ID"], ""),
    group=12,
)
async def user_id(client, message):
    user = message.from_user
    chat = message.chat

    base_text = f"""<b>• الاسم: <a href="tg://user?id={user.id}">{user.first_name}</a>
• المعرف: @{user.username or 'لا يوجد'}
• الايدي: <code>{user.id}</code>
• الدردشه: {chat.title or 'خاص'}
• ايدي الدردشه: <code>{chat.id}</code></b>
ㅤ"""

    return await send_id_card(
        client, message, user.id, base_text, user.first_name
    )


if __name__ == "__main__":
    print("الترخيص: @TopVeGa\n العلامة التجارية: VEGA & لوجيك | Logic™\nحقوق الطبع والنشر: © 2015 - 2025")
    app.run()
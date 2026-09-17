#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VK Парсер → Telegram бот
Каждые 2 часа присылает ссылки на подходящие посты
"""

import requests
import time
import os
import json
import threading
import schedule
from datetime import datetime, timezone, timedelta

# ══════════════════════════════════════════════════════════
TG_TOKEN = "8831015403:AAF7xa9flVldobGjEJyRiuKkQbraZSkD1_E"
VK_TOKEN = "vk1.a.2prxvO3cCOd9T7XGATkgXD5ssMfX-e7_q3JAx0NyzOoiLA5URGjaYsM0VmZndgVzM_-Lk8nBLEoO4oQU9TMg1mXsDywcRfejcuEoINZ_yPOMhToTIvksNwY8xVpyXomnpLX1CUyYTR3MHJajUyH7EsW-MIzgXoVixOghQknF0ZKHE3cB_NQyAoSHxhuliGrDMyMa5eFyrsBnqEW4md6Isw"
# ══════════════════════════════════════════════════════════

MSK        = timezone(timedelta(hours=3))
TG_API     = f"https://api.telegram.org/bot{TG_TOKEN}"
SUBS_FILE  = "subscribers.json"

# ─── Подписчики ───────────────────────────────────────────────────────────────

def load_subscribers() -> set:
    if os.path.exists(SUBS_FILE):
        try:
            return set(json.load(open(SUBS_FILE, encoding="utf-8")))
        except Exception:
            pass
    return set()

def save_subscribers(subs: set):
    json.dump(list(subs), open(SUBS_FILE, "w", encoding="utf-8"))

subscribed_chats = load_subscribers()

# ─── Группы ───────────────────────────────────────────────────────────────────

GROUPS = [
    {"id": "magnitkacity",         "name": "Черное и белое"},
    {"id": "nashmgn",              "name": "Наш Магнитогорск"},
    {"id": "novostimagnitogorska", "name": "Новости Магнитогорска"},
    {"id": "club54793836",         "name": "Подслушано Магнитогорск"},
    {"id": "urban_mgn",            "name": "Урбанистика и архитектура"},
    {"id": "public207727080",      "name": "Магнитка. Левый берег"},
    {"id": "club49177878",         "name": "На дорогах Магнитки"},
    {"id": "zhurnalspletni",       "name": "Журнал сплетни"},
    {"id": "stas_naumov_2026",     "name": "Стас Наумов 2026"},
]

NO_FILTER_GROUPS = [
    {"id": "deputatnaumov", "name": "Депутат Наумов"},
]

# ─── Темы ─────────────────────────────────────────────────────────────────────

TOPICS = {
    "ЖКХ": [
        "жкх", "жилищно-коммунальн", "управляющая компания", " ук ", "тсж",
        "капитальный ремонт", "подъезд", "лифт", "мусор", "отходы", "свалка",
        "канализация", "трубы", "прорыв", "затопил", "колодец", "люк",
        "городское хозяйство", "коммунальщик",
    ],
    "Теплоснабжение": [
        "тепло", "теплофикация", "теплоснабжение", "отопление", "батарея",
        "горячая вода", "отключили воду", "отключили отопление", "теплосеть",
        "без тепла",
    ],
    "Водоканал": [
        "водоканал", "водоснабжение", "холодная вода", "водопровод",
        "давление воды", "нет воды",
    ],
    "Транспорт / МАГГОРТРАНС": [
        "маггортранс", "автобус", "троллейбус", "трамвай", "маршрут",
        "общественный транспорт", "остановка", "расписание",
        "пассажир", "водитель автобуса",
    ],
    "Дороги и ямы": [
        "яма", "ямочный ремонт", "асфальт", "ремонт дорог", "тротуар",
        "бордюр", "дорожники", "разбитая дорога", "ухаб",
    ],
    "Экология": [
        "экология", "экологич", "загрязнение", "выброс", "смог",
        "качество воздуха", "ммк", "пыль", "пылевое облако", "задымление",
        "вырубка деревьев",
    ],
    "Парки и благоустройство": [
        "парк", "сквер", "благоустройство", "газон", "озеленение",
        "детская площадка", "фонтан", "набережная", "аллея",
    ],
    "Горэлектросеть": [
        "горэлектросеть", "электричество", "отключили свет", "нет света",
        "электроснабжение", "фонари", "освещение улиц", "подстанция", "обесточил",
    ],
    "Глава города / Бердников": [
        "бердников", "глава города", "мэр города", "администрация города",
        "городская дума", "муниципалитет", "глава администрации",
    ],
    "Здравоохранение": [
        "больниц", "поликлиник", "врач", "медицин", "скорая помощь",
        "здравоохранение", "аптека", "лекарств", "стационар",
        "запись к врачу", "фельдшер",
    ],
    "Образование": [
        "школ", "детский сад", "садик", "вуз", "колледж", "образование",
        "учитель", "педагог", "ученик", "учебный год", "егэ", "огэ", "мгту",
    ],
    "Мигранты": [
        "мигрант", "гастарбайтер", "иностранный рабочий", "нелегал",
        "депортация", "миграция",
    ],
}

EXCLUDE = [
    "купить", "скидк", "распродаж", "интернет-магазин",
    "бпла", "беспилотная опасность",
    "розыгрыш", "акция", "акции", "конкурс", "скидки",
]

# ─── Telegram API ─────────────────────────────────────────────────────────────

def tg_send(chat_id, text: str):
    """Отправляет сообщение. Длинные бьёт на части (лимит TG — 4096 символов)."""
    chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
    for chunk in chunks:
        try:
            requests.post(
                f"{TG_API}/sendMessage",
                json={"chat_id": chat_id, "text": chunk,
                      "disable_web_page_preview": True},
                timeout=10,
            )
            if len(chunks) > 1:
                time.sleep(0.3)
        except Exception as e:
            print(f"  [!] Ошибка отправки в TG: {e}")


def tg_delete_webhook():
    """Удаляет webhook если был установлен — иначе getUpdates вернёт 409."""
    try:
        resp = requests.post(
            f"{TG_API}/deleteWebhook",
            json={"drop_pending_updates": True},
            timeout=10,
        )
        print(f"  deleteWebhook: {resp.json().get('description', '')}")
    except Exception as e:
        print(f"  [!] deleteWebhook ошибка: {e}")


def tg_get_updates(offset=None) -> list:
    try:
        params = {"timeout": 30, "limit": 100}
        if offset:
            params["offset"] = offset
        resp = requests.get(f"{TG_API}/getUpdates", params=params, timeout=40)
        resp.raise_for_status()
        data = resp.json()
        return data.get("result", [])
    except Exception as e:
        print(f"  [!] Ошибка polling: {e}")
        time.sleep(5)
        return []


def bot_polling():
    """Слушает входящие сообщения в фоновом потоке."""
    global subscribed_chats
    tg_delete_webhook()
    offset = None
    print("Telegram бот запущен. Ожидаю /start...")

    while True:
        try:
            if not TG_TOKEN:
                print("[!!!] TG_TOKEN пустой! Проверьте переменные окружения.")
                time.sleep(60)
                continue

            updates = tg_get_updates(offset)

            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message", {})
                if not msg:
                    continue

                text    = msg.get("text", "").strip().lower()
                chat_id = msg["chat"]["id"]

                if text in ("/start", "start", "старт"):
                    subscribed_chats.add(chat_id)
                    save_subscribers(subscribed_chats)
                    tg_send(chat_id,
                        "✅ Вы подписаны на рассылку!\n\n"
                        "Каждые 2 часа буду присылать ссылки на посты "
                        "из городских групп Магнитогорска.\n\n"
                        "Команды:\n"
                        "/stop — отписаться\n"
                        "/now — получить посты прямо сейчас"
                    )
                    print(f"  [+] Подписчик: {chat_id}")

                elif text in ("/stop", "stop"):
                    subscribed_chats.discard(chat_id)
                    save_subscribers(subscribed_chats)
                    tg_send(chat_id, "Вы отписаны. Напишите /start чтобы подписаться снова.")
                    print(f"  [-] Отписка: {chat_id}")

                elif text in ("/now", "now", "сейчас"):
                    tg_send(chat_id, "Собираю посты, подождите...")
                    threading.Thread(
                        target=run_parser_for,
                        args=([chat_id],),
                        daemon=True
                    ).start()

        except Exception as e:
            print(f"  [!] Ошибка в polling: {e}")
            time.sleep(5)

# ─── VK API ───────────────────────────────────────────────────────────────────

def fetch_posts(group_id: str) -> list:
    for attempt in range(3):
        try:
            resp = requests.get(
                "https://api.vk.com/method/wall.get",
                params={
                    "domain":       group_id,
                    "count":        100,
                    "filter":       "owner",
                    "access_token": VK_TOKEN,
                    "v":            "5.199",
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                code = data["error"]["error_code"]
                msg  = data["error"]["error_msg"]
                if code in (5, 1116):
                    print(f"  [!!!] ТОКЕН VK НЕДЕЙСТВИТЕЛЕН (код {code}).")
                    return []
                if code in (6, 9):
                    print(f"  [!] VK flood, жду 10 секунд...")
                    time.sleep(10)
                    continue
                print(f"  [!] VK API {code}: {msg}")
                return []
            return data["response"].get("items", [])
        except requests.exceptions.ConnectionError:
            print(f"  [!] Нет соединения (попытка {attempt+1}/3)")
            time.sleep(3)
        except Exception as e:
            print(f"  [!] Ошибка {group_id}: {e}")
            return []
    return []


def extract_text(post: dict) -> str:
    parts = []
    t = post.get("text", "").strip()
    if t:
        parts.append(t)
    for orig in post.get("copy_history", []):
        t = orig.get("text", "").strip()
        if t:
            parts.append(t)
    for att in post.get("attachments", []):
        atype = att.get("type", "")
        if atype == "video":
            v = att.get("video", {})
            if v.get("title"):       parts.append(v["title"].strip())
            if v.get("description"): parts.append(v["description"].strip())
        elif atype == "article":
            a = att.get("article", {})
            if a.get("title"):       parts.append(a["title"].strip())
        elif atype == "link":
            lnk = att.get("link", {})
            if lnk.get("title"):       parts.append(lnk["title"].strip())
            if lnk.get("description"): parts.append(lnk["description"].strip())
    return " ".join(parts)


def match_topics(text: str) -> bool:
    tl = text.lower()
    for ex in EXCLUDE:
        if ex.lower() in tl:
            return False
    for keywords in TOPICS.values():
        for kw in keywords:
            if kw.lower() in tl:
                return True
    return False


def now_msk() -> datetime:
    return datetime.now(tz=MSK)

def post_dt_msk(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=MSK)

# ─── Сбор постов ──────────────────────────────────────────────────────────────

last_run_time: datetime = None


def collect_urls(window_from: datetime, window_to: datetime) -> list:
    urls = []

    for group in GROUPS:
        for p in fetch_posts(group["id"]):
            ts = p.get("date", 0)
            dt = post_dt_msk(ts)
            if not (window_from <= dt < window_to):
                continue
            text = extract_text(p)
            if not text or not match_topics(text):
                continue
            urls.append(f"https://vk.com/wall{p.get('owner_id')}_{p.get('id')}")
        time.sleep(1)

    for group in NO_FILTER_GROUPS:
        for p in fetch_posts(group["id"]):
            ts = p.get("date", 0)
            dt = post_dt_msk(ts)
            if not (window_from <= dt < window_to):
                continue
            urls.append(f"https://vk.com/wall{p.get('owner_id')}_{p.get('id')}")
        time.sleep(1)

    return urls


def run_parser_for(chat_ids: list, window_from=None, window_to=None):
    now = now_msk()
    if window_to is None:
        window_to = now
    if window_from is None:
        window_from = now - timedelta(hours=2)

    period = f"{window_from.strftime('%H:%M')}–{window_to.strftime('%H:%M')} МСК"
    print(f"Парсинг {period}...")

    urls = collect_urls(window_from, window_to)

    if urls:
        msg = f"📋 {period} — {len(urls)} постов:\n\n" + "\n".join(urls)
    else:
        msg = f"За {period} подходящих постов не найдено."

    for chat_id in chat_ids:
        tg_send(chat_id, msg)
        print(f"  → {chat_id}: {len(urls)} ссылок")


def run_parser():
    global last_run_time
    now         = now_msk()
    window_from = last_run_time if last_run_time else (now - timedelta(hours=2))
    window_to   = now
    last_run_time = now

    if not subscribed_chats:
        print("Нет подписчиков, пропускаю.")
        return

    run_parser_for(list(subscribed_chats), window_from, window_to)
    print("Следующий запуск через 2 часа.\n")

# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not TG_TOKEN:
        print("[!] TG_TOKEN не задан!")
        exit(1)
    if not VK_TOKEN:
        print("[!] VK_TOKEN не задан!")
        exit(1)

    print("VK Парсер → Telegram бот · Магнитогорск")
    print(f"Подписчиков загружено: {len(subscribed_chats)}")

    threading.Thread(target=bot_polling, daemon=True).start()
    run_parser()
    schedule.every(2).hours.do(run_parser)
    while True:
        schedule.run_pending()
        time.sleep(30)

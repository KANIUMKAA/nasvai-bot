import json, time, secrets, string, logging
import urllib.request as ur

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
BOT_TOKEN       = "8742859803:AAGrm360Y2ACoIdkmMp527xB10sEglSyb1w"
JSONBIN_BIN_ID  = "6ade6c721d04ca511c017232"
JSONBIN_API_KEY = "$2a$10$m4N9TF51UIqiVMSdAabz2OqPVuNkhiNBSl4LhMQ4Zm9x43T2r4zIm"
ADMINS          = {8065732584, 7170665123}
JSONBIN_URL     = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"

PAYMENT_INFO = (
    "💳 <b>Реквізити для оплати:</b>\n"
    "Monobank: <code>4441 1144 XXXX XXXX</code>\n"
    "Отримувач: Ім'я Прізвище"
)

PRICES = {
    "7d":   {"label": "На неделю",  "hours": 168,   "price": "56 ⭐ або 40 грн"},
    "30d":  {"label": "На месяц",   "hours": 720,   "price": "112 ⭐ або 80 грн"},
    "180d": {"label": "На полгода", "hours": 4320,  "price": "280 ⭐ або 200 грн"},
    "perm": {"label": "Навсегда",   "hours": 87600, "price": "420 ⭐ або 300 грн"},
}
# ─────────────────────────────────────────────────────────────────────────────

TG = f"https://api.telegram.org/bot{BOT_TOKEN}"
JB_HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY,
    "X-Bin-Versioning": "false",
}

# pending[user_id] = {"plan": pid}
pending = {}

# ── JSONBin ───────────────────────────────────────────────────────────────────
def jb_read():
    try:
        req = ur.Request(JSONBIN_URL + "/latest", headers=JB_HEADERS)
        with ur.urlopen(req, timeout=6) as r:
            return json.loads(r.read()).get("record", {})
    except: return {}

def jb_write(record):
    try:
        req = ur.Request(JSONBIN_URL, data=json.dumps(record).encode(),
                         headers=JB_HEADERS, method="PUT")
        with ur.urlopen(req, timeout=6): return True
    except: return False

def create_key(hours):
    chars = string.ascii_uppercase + string.digits
    key = "NV-" + "-".join(''.join(secrets.choice(chars) for _ in range(5)) for _ in range(4))
    expiry = time.time() + hours * 3600
    db = jb_read() or {}
    db.setdefault("user_keys", {})
    now = time.time()
    db["user_keys"] = {k: v for k, v in db["user_keys"].items() if v > now}
    db["user_keys"][key] = expiry
    jb_write(db)
    return key, expiry

def fmt_dt(ts):
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")

# ── Telegram ──────────────────────────────────────────────────────────────────
def tg(method, **params):
    try:
        body = json.dumps(params).encode()
        req = ur.Request(f"{TG}/{method}", data=body,
                         headers={"Content-Type": "application/json"}, method="POST")
        with ur.urlopen(req, timeout=35) as r:
            return json.loads(r.read())
    except Exception as e:
        return {}

def send(chat_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup: p["reply_markup"] = json.dumps(markup)
    return tg("sendMessage", **p)

def edit(chat_id, msg_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "message_id": msg_id,
         "text": text, "parse_mode": parse_mode}
    if markup: p["reply_markup"] = json.dumps(markup)
    return tg("editMessageText", **p)

def forward_photo(from_chat, msg_id, to_chat):
    tg("forwardMessage", chat_id=to_chat,
       from_chat_id=from_chat, message_id=msg_id)

def answer_cb(cb_id, text=""):
    tg("answerCallbackQuery", callback_query_id=cb_id, text=text, show_alert=False)

# ── Keyboards ─────────────────────────────────────────────────────────────────
def kb_main():
    return {"inline_keyboard": [
        [{"text": "🛒 Купити ключ", "callback_data": "buy"}],
        [{"text": "ℹ️ Про лаунчер", "callback_data": "about"}],
    ]}

def kb_plans():
    rows = [[{"text": f"{p['label']} — {p['price']}", "callback_data": f"plan_{k}"}]
            for k, p in PRICES.items()]
    rows.append([{"text": "◀️ Назад", "callback_data": "main"}])
    return {"inline_keyboard": rows}

def kb_admin_confirm(user_id, plan):
    return {"inline_keyboard": [[
        {"text": "✅ Видати ключ", "callback_data": f"confirm_{user_id}_{plan}"},
        {"text": "❌ Відхилити",   "callback_data": f"reject_{user_id}"},
    ]]}

def kb_back():
    return {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": "main"}]]}

# ── Logic ─────────────────────────────────────────────────────────────────────
def on_start(chat_id, uid, name):
    is_admin = uid in ADMINS
    if is_admin:
        send(chat_id,
             f"👑 <b>Адмін-панель</b>, {name}\n\n"
             f"Очікуй скріншоти оплати від користувачів.\n"
             f"Після перевірки натискай ✅ і ключ відправиться автоматично.")
    else:
        send(chat_id,
             f"👋 Привіт, <b>{name}</b>!\n\n"
             f"Це бот <b>Nasvai Visual Launcher</b>.\n"
             f"Тут можна купити ключ активації.",
             markup=kb_main())

def on_callback(chat_id, msg_id, uid, name, data):
    is_admin = uid in ADMINS

    if data == "main":
        edit(chat_id, msg_id,
             f"👋 Привіт, <b>{name}</b>! Обери дію:",
             markup=kb_main())

    elif data == "about":
        edit(chat_id, msg_id,
             "ℹ️ <b>Nasvai Visual Launcher</b>\n\n"
             "🎮 Minecraft 1.21.4 + Fabric\n"
             "🔑 Ключі з часовим обмеженням\n\n"
             "Купи ключ — і грай!",
             markup=kb_back())

    elif data == "buy":
        edit(chat_id, msg_id,
             "🛒 <b>Выбери тариф:</b>",
             markup=kb_plans())

    elif data.startswith("plan_"):
        pid = data[5:]
        if pid not in PRICES: return
        p = PRICES[pid]
        pending[uid] = {"plan": pid}
        desc = {
            "7d":   "7 дней · Полная сборка NASVAI-VISUAL\nВсе функции: небо, частицы, звуки, текстуры\nПоддержка в Telegram",
            "30d":  "30 дней · Полная сборка NASVAI-VISUAL\nВсе функции: небо, частицы, звуки, текстуры\nПоддержка в Telegram",
            "180d": "6 месяцев · Полная сборка NASVAI-VISUAL\nВсе функции: небо, частицы, звуки, текстуры\nПоддержка в Telegram",
            "perm": "10 лет · Полная сборка NASVAI-VISUAL\nВсе функции: небо, частицы, звуки, текстуры\nПриоритетная поддержка",
        }.get(pid, "")
        edit(chat_id, msg_id,
             f"💰 <b>{p['label']} — {p['price']}</b>\n\n"
             f"✅ {desc}\n\n"
             f"{PAYMENT_INFO}\n\n"
             f"Після оплати надішли <b>скріншот</b> сюди 👇\n"
             f"Ключ прийде автоматично після перевірки ⚡",
             markup=kb_back())

    # Адмін підтверджує
    elif data.startswith("confirm_") and is_admin:
        parts = data.split("_")
        target_uid = int(parts[1])
        pid = parts[2]
        if pid not in PRICES: return
        p = PRICES[pid]
        key, expiry = create_key(p["hours"])
        # Відправляємо ключ юзеру
        send(target_uid,
             f"🎉 <b>Оплату підтверджено!</b>\n\n"
             f"🔑 Твій ключ:\n<code>{key}</code>\n\n"
             f"⏱ Тариф: {p['label']}\n"
             f"📅 Діє до: {fmt_dt(expiry)}\n\n"
             f"Введи ключ у лаунчері та грай! 🎮")
        # Оновлюємо повідомлення адміна
        edit(chat_id, msg_id,
             f"✅ <b>Ключ видано!</b>\n\n"
             f"👤 Юзер: <code>{target_uid}</code>\n"
             f"📦 Тариф: {p['label']}\n"
             f"🔑 <code>{key}</code>")
        if target_uid in pending:
            del pending[target_uid]

    # Адмін відхиляє
    elif data.startswith("reject_") and is_admin:
        target_uid = int(data[7:])
        send(target_uid,
             "❌ <b>Оплату не підтверджено.</b>\n\n"
             "Можливо скріншот нечіткий або сума не співпадає.\n"
             "Спробуй ще раз або напиши адміну.",
             markup=kb_main())
        edit(chat_id, msg_id, "❌ Відхилено.")
        if target_uid in pending:
            del pending[target_uid]

def on_message(chat_id, uid, name, text=None, photo=None):
    # Юзер надіслав скріншот
    if photo and uid in pending and uid not in ADMINS:
        pid = pending[uid]["plan"]
        p = PRICES[pid]
        # Пересилаємо скріншот кожному адміну з кнопками
        for admin_id in ADMINS:
            forward_photo(chat_id, photo, admin_id)
            send(admin_id,
                 f"💰 <b>Нова оплата!</b>\n\n"
                 f"👤 {name} (ID: <code>{uid}</code>)\n"
                 f"📦 {p['label']} — {p['price']}\n\n"
                 f"Перевір скріншот вище і підтверди:",
                 markup=kb_admin_confirm(uid, pid))
        send(chat_id,
             "⏳ Скріншот отримано!\n"
             "Адмін перевіряє оплату — ключ надійде автоматично.")
        return

    if text and text.startswith("/start"):
        on_start(chat_id, uid, name)
        return

    # Будь-яке інше — показуємо меню
    if uid not in ADMINS:
        send(chat_id, "Обери дію:", markup=kb_main())

# ── Polling ───────────────────────────────────────────────────────────────────
def run():
    logging.info("Bot started")
    offset = 0
    while True:
        try:
            r = tg("getUpdates", offset=offset, timeout=30)
            for upd in r.get("result", []):
                offset = upd["id"] + 1
                try:
                    if "callback_query" in upd:
                        cb   = upd["callback_query"]
                        uid  = cb["from"]["id"]
                        name = cb["from"].get("first_name", "User")
                        cid  = cb["message"]["chat"]["id"]
                        mid  = cb["message"]["message_id"]
                        answer_cb(cb["id"])
                        logging.info(f"CB uid={uid} data={cb['data']}")
                        on_callback(cid, mid, uid, name, cb["data"])

                    elif "message" in upd:
                        msg  = upd["message"]
                        uid  = msg["from"]["id"]
                        name = msg["from"].get("first_name", "User")
                        cid  = msg["chat"]["id"]
                        text = msg.get("text")
                        photo = None
                        if "photo" in msg:
                            photo = msg["photo"][-1]["file_id"]
                        logging.info(f"MSG uid={uid} text={text!r} photo={'yes' if photo else 'no'}")
                        on_message(cid, uid, name, text, photo)
                except Exception as e:
                    logging.exception(f"Update error: {e}")
        except Exception as e:
            logging.warning(f"Polling error: {e}")
            time.sleep(3)

if __name__ == "__main__":
    run()

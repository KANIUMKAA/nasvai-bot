import json, time, secrets, logging
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
SUPPORT         = "@NASVAIVISUAL"

PAYMENT_INFO = (
    "💳 <b>Реквізити для оплати:</b>\n"
    "Monobank: <code>4874 0700 3270 3702</code>\n"
    "⭐ Зірки Telegram: @NASVAIVISUAL"
)

ALPHABET = "ABCDEFGHJKLMNPQRTUVWXY3469"  # той самий що й у лаунчері

PRICES = {
    "7d":   {"label": "На тиждень",  "hours": 168,   "price": "56 ⭐ або 40 грн"},
    "30d":  {"label": "На місяць",   "hours": 720,   "price": "112 ⭐ або 80 грн"},
    "180d": {"label": "На пів року", "hours": 4320,  "price": "280 ⭐ або 200 грн"},
    "perm": {"label": "Назавжди",    "hours": 87600, "price": "420 ⭐ або 300 грн"},
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
    except:
        return {}

def jb_write(record):
    try:
        req = ur.Request(JSONBIN_URL, data=json.dumps(record).encode(),
                         headers=JB_HEADERS, method="PUT")
        with ur.urlopen(req, timeout=6):
            return True
    except:
        return False

def create_key(hours):
    key = "NV-" + "-".join(
        ''.join(secrets.choice(ALPHABET) for _ in range(5))
        for _ in range(4)
    )
    expiry = time.time() + hours * 3600
    db = jb_read() or {}
    db.setdefault("user_keys", {})
    now = time.time()
    # Видаляємо прострочені ключі
    db["user_keys"] = {k: v for k, v in db["user_keys"].items() if v > now}
    db["user_keys"][key] = expiry
    jb_write(db)
    return key, expiry

def delete_key(key):
    db = jb_read() or {}
    db.setdefault("user_keys", {})
    if key in db["user_keys"]:
        del db["user_keys"][key]
        jb_write(db)
        return True
    return False

def get_all_keys():
    """Повертає {key: expiry} тільки активні"""
    db = jb_read() or {}
    now = time.time()
    return {k: v for k, v in db.get("user_keys", {}).items() if v > now}

def get_user_key(uid):
    """Шукаємо ключ юзера в базі (збережений у user_data)"""
    db = jb_read() or {}
    user_data = db.get("user_data", {})
    key = user_data.get(str(uid), {}).get("key", "")
    if not key:
        return None, None
    # Перевіряємо чи ключ ще активний
    user_keys = db.get("user_keys", {})
    expiry = user_keys.get(key)
    if expiry and expiry > time.time():
        return key, expiry
    return key, None  # ключ є але прострочений

def save_user_key(uid, key):
    """Прив'язуємо ключ до юзера"""
    db = jb_read() or {}
    db.setdefault("user_data", {})
    db["user_data"].setdefault(str(uid), {})
    db["user_data"][str(uid)]["key"] = key
    jb_write(db)

def fmt_dt(ts):
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")

def fmt_remaining(ts):
    remaining = ts - time.time()
    if remaining <= 0:
        return "прострочено"
    days = int(remaining // 86400)
    hours = int((remaining % 86400) // 3600)
    if days > 365:
        return "Назавжди"
    if days > 0:
        return f"{days} дн. {hours} год."
    return f"{hours} год."

# ── Telegram ──────────────────────────────────────────────────────────────────
def tg(method, **params):
    try:
        body = json.dumps(params).encode()
        req = ur.Request(f"{TG}/{method}", data=body,
                         headers={"Content-Type": "application/json"}, method="POST")
        with ur.urlopen(req, timeout=35) as r:
            return json.loads(r.read())
    except:
        return {}

def send(chat_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if markup:
        p["reply_markup"] = json.dumps(markup)
    return tg("sendMessage", **p)

def edit(chat_id, msg_id, text, markup=None, parse_mode="HTML"):
    p = {"chat_id": chat_id, "message_id": msg_id,
         "text": text, "parse_mode": parse_mode}
    if markup:
        p["reply_markup"] = json.dumps(markup)
    return tg("editMessageText", **p)

def forward_photo(from_chat, msg_id, to_chat):
    tg("forwardMessage", chat_id=to_chat,
       from_chat_id=from_chat, message_id=msg_id)

def answer_cb(cb_id, text="", alert=False):
    tg("answerCallbackQuery", callback_query_id=cb_id,
       text=text, show_alert=alert)

# ── Keyboards ─────────────────────────────────────────────────────────────────
def kb_main():
    return {"inline_keyboard": [
        [{"text": "👤 Мій кабінет",  "callback_data": "cabinet"}],
        [{"text": "🛒 Купити ключ",   "callback_data": "buy"}],
        [{"text": "ℹ️ Про лаунчер",   "callback_data": "about"}],
        [{"text": "💬 Підтримка",     "callback_data": "support"}],
    ]}

def kb_cabinet(has_active_key):
    rows = [
        [{"text": "🔑 Мої ключі", "callback_data": "my_keys"}],
    ]
    if has_active_key:
        rows.append([{"text": "🛒 Купити ще ключ", "callback_data": "buy"}])
    else:
        rows.append([{"text": "🛒 Купити ключ", "callback_data": "buy"}])
    rows.append([{"text": "💬 Підтримка", "callback_data": "support"}])
    rows.append([{"text": "◀️ Назад", "callback_data": "main"}])
    return {"inline_keyboard": rows}

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

def kb_back(to="main"):
    return {"inline_keyboard": [[{"text": "◀️ Назад", "callback_data": to}]]}

def kb_admin_main():
    return {"inline_keyboard": [
        [{"text": "🔑 Всі активні ключі", "callback_data": "admin_keys"}],
        [{"text": "➕ Видати ключ вручну", "callback_data": "admin_give"}],
        [{"text": "📊 Статистика",         "callback_data": "admin_stats"}],
    ]}

def kb_admin_keys_list(keys):
    rows = []
    for key, expiry in list(keys.items())[:10]:  # показуємо перші 10
        short = key[-9:]  # останні 9 символів
        rows.append([{"text": f"🔑 ...{short} | {fmt_remaining(expiry)}",
                      "callback_data": f"admin_del_{key}"}])
    rows.append([{"text": "◀️ Назад", "callback_data": "admin_panel"}])
    return {"inline_keyboard": rows}

def kb_admin_give_plan():
    rows = [[{"text": f"{p['label']}", "callback_data": f"admin_give_plan_{k}"}]
            for k, p in PRICES.items()]
    rows.append([{"text": "◀️ Назад", "callback_data": "admin_panel"}])
    return {"inline_keyboard": rows}

# ── Logic ─────────────────────────────────────────────────────────────────────
def show_main(chat_id, uid, name, msg_id=None):
    text = (
        f"👋 Привіт, <b>{name}</b>!\n\n"
        f"🎮 Це бот <b>Nasvai Visual Launcher</b>\n"
        f"Minecraft 1.21.4 + Fabric\n\n"
        f"Обери дію нижче 👇"
    )
    if msg_id:
        edit(chat_id, msg_id, text, markup=kb_main())
    else:
        send(chat_id, text, markup=kb_main())

def show_cabinet(chat_id, uid, name, msg_id=None):
    key, expiry = get_user_key(uid)

    if key and expiry:
        key_status = (
            f"✅ <b>Ключ активний</b>\n"
            f"🔑 <code>{key}</code>\n"
            f"⏱ Залишилось: <b>{fmt_remaining(expiry)}</b>\n"
            f"📅 Діє до: {fmt_dt(expiry)}"
        )
        has_active = True
    elif key and not expiry:
        key_status = (
            f"❌ <b>Ключ прострочено</b>\n"
            f"🔑 <code>{key}</code>\n\n"
            f"Купи новий ключ щоб продовжити грати!"
        )
        has_active = False
    else:
        key_status = (
            f"🚫 <b>Ключа немає</b>\n\n"
            f"Купи ключ щоб активувати лаунчер!"
        )
        has_active = False

    text = (
        f"👤 <b>Мій кабінет</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"👤 {name}\n"
        f"🆔 <code>{uid}</code>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{key_status}"
    )

    if msg_id:
        edit(chat_id, msg_id, text, markup=kb_cabinet(has_active))
    else:
        send(chat_id, text, markup=kb_cabinet(has_active))

def show_my_keys(chat_id, uid, name, msg_id=None):
    key, expiry = get_user_key(uid)

    if key and expiry:
        text = (
            f"🔑 <b>Твій ключ</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<code>{key}</code>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"✅ Статус: <b>Активний</b>\n"
            f"⏱ Залишилось: <b>{fmt_remaining(expiry)}</b>\n"
            f"📅 Діє до: <b>{fmt_dt(expiry)}</b>\n\n"
            f"Скопіюй ключ та введи у лаунчері 🎮"
        )
    elif key and not expiry:
        text = (
            f"🔑 <b>Твій ключ</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"<code>{key}</code>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"❌ Статус: <b>Прострочено</b>\n\n"
            f"Купи новий ключ 👇"
        )
    else:
        text = (
            f"🔑 <b>Мої ключі</b>\n\n"
            f"🚫 У тебе ще немає ключа\n\n"
            f"Купи ключ щоб активувати лаунчер 👇"
        )

    rows = [
        [{"text": "🛒 Купити ключ", "callback_data": "buy"}],
        [{"text": "◀️ Назад", "callback_data": "cabinet"}],
    ]

    if msg_id:
        edit(chat_id, msg_id, text, markup={"inline_keyboard": rows})
    else:
        send(chat_id, text, markup={"inline_keyboard": rows})

def on_start(chat_id, uid, name):
    if uid in ADMINS:
        send(chat_id,
             f"👑 <b>Адмін-панель</b>, {name}!\n\n"
             f"Очікуй скріншоти оплати від юзерів.\n"
             f"Після перевірки натискай ✅\n\n"
             f"Або керуй ключами вручну:",
             markup=kb_admin_main())
    else:
        show_main(chat_id, uid, name)

def on_callback(chat_id, msg_id, uid, name, data):
    is_admin = uid in ADMINS

    # ── ГОЛОВНЕ МЕНЮ ──────────────────────────────────────────────────────────
    if data == "main":
        show_main(chat_id, uid, name, msg_id)

    # ── КАБІНЕТ ───────────────────────────────────────────────────────────────
    elif data == "cabinet":
        show_cabinet(chat_id, uid, name, msg_id)

    elif data == "my_keys":
        show_my_keys(chat_id, uid, name, msg_id)

    # ── ПРО ЛАУНЧЕР ───────────────────────────────────────────────────────────
    elif data == "about":
        edit(chat_id, msg_id,
             "ℹ️ <b>Nasvai Visual Launcher</b>\n\n"
             "🎮 Minecraft 1.21.4 + Fabric\n"
             "🔑 Ключі з часовим обмеженням\n"
             "🎨 Кастомне небо, частинки, звуки, текстури\n"
             "⚡ Автооновлення\n\n"
             f"💬 Підтримка: {SUPPORT}",
             markup=kb_back())

    # ── ПІДТРИМКА ─────────────────────────────────────────────────────────────
    elif data == "support":
        edit(chat_id, msg_id,
             f"💬 <b>Підтримка</b>\n\n"
             f"Є питання? Пиши сюди:\n"
             f"👉 {SUPPORT}\n\n"
             f"Відповімо якомога швидше 🚀",
             markup=kb_back())

    # ── КУПИТИ ────────────────────────────────────────────────────────────────
    elif data == "buy":
        edit(chat_id, msg_id,
             "🛒 <b>Вибери тариф:</b>",
             markup=kb_plans())

    elif data.startswith("plan_"):
        pid = data[5:]
        if pid not in PRICES:
            return
        p = PRICES[pid]
        pending[uid] = {"plan": pid}
        desc = {
            "7d":   "7 днів · Повна збірка NASVAI-VISUAL\nВсі функції: небо, частинки, звуки, текстури\nПідтримка в Telegram",
            "30d":  "30 днів · Повна збірка NASVAI-VISUAL\nВсі функції: небо, частинки, звуки, текстури\nПідтримка в Telegram",
            "180d": "6 місяців · Повна збірка NASVAI-VISUAL\nВсі функції: небо, частинки, звуки, текстури\nПідтримка в Telegram",
            "perm": "10 років · Повна збірка NASVAI-VISUAL\nВсі функції: небо, частинки, звуки, текстури\nПріоритетна підтримка",
        }.get(pid, "")
        edit(chat_id, msg_id,
             f"💰 <b>{p['label']} — {p['price']}</b>\n\n"
             f"✅ {desc}\n\n"
             f"━━━━━━━━━━━━━━━\n"
             f"{PAYMENT_INFO}\n"
             f"━━━━━━━━━━━━━━━\n\n"
             f"Після оплати надішли <b>скріншот</b> сюди 👇\n"
             f"Ключ прийде автоматично після перевірки ⚡",
             markup=kb_back())

    # ── АДМІН: підтвердити оплату ─────────────────────────────────────────────
    elif data.startswith("confirm_") and is_admin:
        parts = data.split("_")
        target_uid = int(parts[1])
        pid = parts[2]
        if pid not in PRICES:
            return
        p = PRICES[pid]
        key, expiry = create_key(p["hours"])
        save_user_key(target_uid, key)

        send(target_uid,
             f"🎉 <b>Оплату підтверджено!</b>\n\n"
             f"🔑 Твій ключ:\n<code>{key}</code>\n\n"
             f"⏱ Тариф: <b>{p['label']}</b>\n"
             f"📅 Діє до: <b>{fmt_dt(expiry)}</b>\n\n"
             f"Введи ключ у лаунчері та грай! 🎮\n\n"
             f"💬 Підтримка: {SUPPORT}")

        edit(chat_id, msg_id,
             f"✅ <b>Ключ видано!</b>\n\n"
             f"👤 Юзер: <code>{target_uid}</code>\n"
             f"📦 Тариф: {p['label']}\n"
             f"🔑 <code>{key}</code>\n"
             f"📅 До: {fmt_dt(expiry)}")

        if target_uid in pending:
            del pending[target_uid]

    # ── АДМІН: відхилити оплату ───────────────────────────────────────────────
    elif data.startswith("reject_") and is_admin:
        target_uid = int(data[7:])
        send(target_uid,
             "❌ <b>Оплату не підтверджено.</b>\n\n"
             "Можливо скріншот нечіткий або сума не співпадає.\n"
             "Спробуй ще раз або напиши адміну.\n\n"
             f"💬 {SUPPORT}",
             markup=kb_main())
        edit(chat_id, msg_id, "❌ Відхилено.")
        if target_uid in pending:
            del pending[target_uid]

    # ── АДМІН ПАНЕЛЬ ──────────────────────────────────────────────────────────
    elif data == "admin_panel" and is_admin:
        edit(chat_id, msg_id,
             "👑 <b>Адмін-панель</b>\n\nОбери дію:",
             markup=kb_admin_main())

    elif data == "admin_keys" and is_admin:
        keys = get_all_keys()
        if not keys:
            edit(chat_id, msg_id,
                 "🔑 <b>Активні ключі</b>\n\n"
                 "Наразі немає активних ключів.",
                 markup=kb_back("admin_panel"))
        else:
            edit(chat_id, msg_id,
                 f"🔑 <b>Активні ключі ({len(keys)})</b>\n\n"
                 f"Натисни на ключ щоб видалити:",
                 markup=kb_admin_keys_list(keys))

    elif data.startswith("admin_del_") and is_admin:
        key = data[10:]
        delete_key(key)
        answer_cb(data, "✅ Ключ видалено!")
        keys = get_all_keys()
        if not keys:
            edit(chat_id, msg_id,
                 "🔑 <b>Активні ключі</b>\n\nНаразі немає активних ключів.",
                 markup=kb_back("admin_panel"))
        else:
            edit(chat_id, msg_id,
                 f"🔑 <b>Активні ключі ({len(keys)})</b>\n\nНатисни на ключ щоб видалити:",
                 markup=kb_admin_keys_list(keys))

    elif data == "admin_give" and is_admin:
        edit(chat_id, msg_id,
             "➕ <b>Видати ключ вручну</b>\n\n"
             "Вибери тариф:\n"
             "(після вибору надішли мені ID юзера)",
             markup=kb_admin_give_plan())

    elif data.startswith("admin_give_plan_") and is_admin:
        pid = data[16:]
        if pid not in PRICES:
            return
        pending[f"admin_give_{uid}"] = {"plan": pid}
        p = PRICES[pid]
        edit(chat_id, msg_id,
             f"➕ <b>Видати ключ: {p['label']}</b>\n\n"
             f"Надішли мені <b>Telegram ID</b> юзера\n"
             f"(або 0 щоб просто згенерувати ключ без прив'язки)",
             markup=kb_back("admin_give"))

    elif data == "admin_stats" and is_admin:
        keys = get_all_keys()
        db = jb_read() or {}
        users_count = len(db.get("user_data", {}))
        edit(chat_id, msg_id,
             f"📊 <b>Статистика</b>\n\n"
             f"🔑 Активних ключів: <b>{len(keys)}</b>\n"
             f"👥 Юзерів у базі: <b>{users_count}</b>\n"
             f"⏱ Час сервера: {fmt_dt(time.time())}",
             markup=kb_back("admin_panel"))

def on_message(chat_id, uid, name, text=None, photo=None):
    is_admin = uid in ADMINS

    # ── Адмін вводить ID юзера для ручної видачі ключа ───────────────────────
    if is_admin and text and text.isdigit():
        admin_key = f"admin_give_{uid}"
        if admin_key in pending:
            pid = pending[admin_key]["plan"]
            p = PRICES[pid]
            target_uid = int(text)
            key, expiry = create_key(p["hours"])

            if target_uid != 0:
                save_user_key(target_uid, key)
                try:
                    send(target_uid,
                         f"🎉 <b>Адмін видав тобі ключ!</b>\n\n"
                         f"🔑 Твій ключ:\n<code>{key}</code>\n\n"
                         f"⏱ Тариф: <b>{p['label']}</b>\n"
                         f"📅 Діє до: <b>{fmt_dt(expiry)}</b>\n\n"
                         f"Введи ключ у лаунчері та грай! 🎮")
                    user_notified = "✅ Юзера повідомлено"
                except:
                    user_notified = "⚠️ Не вдалось повідомити юзера"
            else:
                user_notified = "ℹ️ Ключ без прив'язки до юзера"

            send(chat_id,
                 f"✅ <b>Ключ згенеровано!</b>\n\n"
                 f"👤 ID юзера: <code>{target_uid if target_uid != 0 else '—'}</code>\n"
                 f"📦 Тариф: {p['label']}\n"
                 f"🔑 <code>{key}</code>\n"
                 f"📅 До: {fmt_dt(expiry)}\n\n"
                 f"{user_notified}",
                 markup=kb_admin_main())
            del pending[admin_key]
            return

    # ── Юзер надіслав скріншот оплати ────────────────────────────────────────
    if photo and uid in pending and not is_admin:
        pid = pending[uid]["plan"]
        p = PRICES[pid]
        for admin_id in ADMINS:
            forward_photo(chat_id, photo, admin_id)
            send(admin_id,
                 f"💰 <b>Нова оплата!</b>\n\n"
                 f"👤 {name} (ID: <code>{uid}</code>)\n"
                 f"📦 {p['label']} — {p['price']}\n\n"
                 f"Перевір скріншот вище і підтверди:",
                 markup=kb_admin_confirm(uid, pid))
        send(chat_id,
             "⏳ <b>Скріншот отримано!</b>\n\n"
             "Адмін перевіряє оплату — ключ надійде автоматично ⚡\n\n"
             f"Якщо є питання: {SUPPORT}")
        return

    # ── /start ────────────────────────────────────────────────────────────────
    if text and text.startswith("/start"):
        on_start(chat_id, uid, name)
        return

    # ── /admin ────────────────────────────────────────────────────────────────
    if text and text.startswith("/admin") and is_admin:
        send(chat_id,
             "👑 <b>Адмін-панель</b>\n\nОбери дію:",
             markup=kb_admin_main())
        return

    # ── Все інше ──────────────────────────────────────────────────────────────
    if not is_admin:
        show_main(chat_id, uid, name)
    else:
        send(chat_id,
             "👑 <b>Адмін-панель</b>\n\nОбери дію:",
             markup=kb_admin_main())

# ── Polling ───────────────────────────────────────────────────────────────────
def run():
    logging.info("Bot started")
    offset = 0
    while True:
        try:
            r = tg("getUpdates", offset=offset, timeout=30)
            for upd in r.get("result", []):
                offset = upd["update_id"] + 1
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

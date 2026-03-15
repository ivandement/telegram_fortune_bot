import asyncio
import os
import random
import re
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    LabeledPrice,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from database import (
    add_coins,
    create_or_update_user,
    get_coins_balance,
    get_free_readings_used,
    get_recent_messages,
    get_user_readings,
    increment_free_readings,
    init_db,
    save_message,
    save_payment,
    save_reading,
    spend_coin,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_TEXT_MODEL = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY не найден")

ai_client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

ASK_NAME, ASK_BIRTHDATE, ASK_EXTRA, ASK_QUESTION, ASK_PHOTO, FOLLOWUP = range(6)

SERVICE_TAROT = "tarot"
SERVICE_ASTRO = "astrology"
SERVICE_NATAL = "natal"
SERVICE_PHOTO = "photo"

COIN_PACKAGES = {
    "coins_1": {"title": "1 монета", "coins": 1, "stars": 25},
    "coins_5": {"title": "5 монет", "coins": 5, "stars": 99},
    "coins_12": {"title": "12 монет", "coins": 12, "stars": 199},
    "coins_25": {"title": "25 монет", "coins": 25, "stars": 399},
}

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🔮 Таро"), KeyboardButton("🌙 Астрология")],
        [KeyboardButton("🪐 Натальная карта"), KeyboardButton("📷 Анализ по фото")],
        [KeyboardButton("🪙 Баланс"), KeyboardButton("⭐ Купить монеты")],
        [KeyboardButton("📜 История"), KeyboardButton("ℹ️ Помощь")],
    ],
    resize_keyboard=True
)

PHOTO_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📷 Пропустить фото")],
        [KeyboardButton("🔮 Таро"), KeyboardButton("🌙 Астрология")],
        [KeyboardButton("🪐 Натальная карта"), KeyboardButton("📷 Анализ по фото")],
        [KeyboardButton("🪙 Баланс"), KeyboardButton("⭐ Купить монеты")],
        [KeyboardButton("📜 История"), KeyboardButton("ℹ️ Помощь")],
    ],
    resize_keyboard=True
)

FOLLOWUP_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("✨ Уточнить ответ")],
        [KeyboardButton("🔮 Таро"), KeyboardButton("🌙 Астрология")],
        [KeyboardButton("🪐 Натальная карта"), KeyboardButton("📷 Анализ по фото")],
        [KeyboardButton("🪙 Баланс"), KeyboardButton("📜 История")],
    ],
    resize_keyboard=True
)

TAROT_CARDS = [
    "Шут", "Маг", "Верховная Жрица", "Императрица", "Император",
    "Иерофант", "Влюбленные", "Колесница", "Сила", "Отшельник",
    "Колесо Фортуны", "Справедливость", "Повешенный", "Смерть",
    "Умеренность", "Дьявол", "Башня", "Звезда", "Луна", "Солнце",
    "Суд", "Мир",
    "Туз Жезлов", "Двойка Жезлов", "Тройка Жезлов", "Четверка Жезлов",
    "Пятерка Жезлов", "Шестерка Жезлов", "Семерка Жезлов", "Восьмерка Жезлов",
    "Девятка Жезлов", "Десятка Жезлов", "Паж Жезлов", "Рыцарь Жезлов",
    "Королева Жезлов", "Король Жезлов",
    "Туз Кубков", "Двойка Кубков", "Тройка Кубков", "Четверка Кубков",
    "Пятерка Кубков", "Шестерка Кубков", "Семерка Кубков", "Восьмерка Кубков",
    "Девятка Кубков", "Десятка Кубков", "Паж Кубков", "Рыцарь Кубков",
    "Королева Кубков", "Король Кубков",
    "Туз Мечей", "Двойка Мечей", "Тройка Мечей", "Четверка Мечей",
    "Пятерка Мечей", "Шестерка Мечей", "Семерка Мечей", "Восьмерка Мечей",
    "Девятка Мечей", "Десятка Мечей", "Паж Мечей", "Рыцарь Мечей",
    "Королева Мечей", "Король Мечей",
    "Туз Пентаклей", "Двойка Пентаклей", "Тройка Пентаклей", "Четверка Пентаклей",
    "Пятерка Пентаклей", "Шестерка Пентаклей", "Семерка Пентаклей", "Восьмерка Пентаклей",
    "Девятка Пентаклей", "Десятка Пентаклей", "Паж Пентаклей", "Рыцарь Пентаклей",
    "Королева Пентаклей", "Король Пентаклей",
]


def is_valid_name(name: str) -> bool:
    name = name.strip()
    if len(name) < 2:
        return False
    return bool(re.fullmatch(r"[A-Za-zА-Яа-яЁё\s\-]+", name))


def is_valid_birthdate(date_str: str) -> bool:
    try:
        datetime.strptime(date_str.strip(), "%d.%m.%Y")
        return True
    except ValueError:
        return False


def get_card_image_path(card_name: str):
    return os.path.join("cards", f"{card_name}.jpg")


def get_service_label(service_type: str) -> str:
    mapping = {
        SERVICE_TAROT: "Таро",
        SERVICE_ASTRO: "Астрология",
        SERVICE_NATAL: "Натальная карта",
        SERVICE_PHOTO: "Анализ по фото",
    }
    return mapping.get(service_type, service_type)


def current_system_prompt(service_type: str) -> str:
    base = (
        "Ты — Мария, внимательная тарологиня и мягкая мудрая проводница. "
        "Ты всегда говоришь от первого лица в женском роде: "
        "'я увидела', 'я чувствую', 'я советую', 'я готова помочь'. "
        "Пиши тепло, глубоко, живо и по-человечески. "
        "Не пиши сухо и шаблонно. "
        "В конце каждого ответа обязательно добавляй отдельный блок с заголовком: 'Что важно сейчас'."
    )

    if service_type == SERVICE_TAROT:
        return base + " Ты делаешь таро-разбор прошлого, настоящего и будущего, опираясь на выпавшие карты."
    if service_type == SERVICE_ASTRO:
        return base + " Ты делаешь астрологический интуитивный разбор на основе даты рождения и вопроса."
    if service_type == SERVICE_NATAL:
        return base + (
            " Ты делаешь интуитивный разбор натальной карты на основе даты рождения, "
            "времени и места рождения. Если данных мало, мягко скажи об ограничениях."
        )
    if service_type == SERVICE_PHOTO:
        return base + " Ты делаешь мягкий визуально-интуитивный анализ по фото и вопросу."
    return base


def ensure_paid_or_free(telegram_id: int) -> tuple[bool, str]:
    used = get_free_readings_used(telegram_id)
    if used < 3:
        increment_free_readings(telegram_id)
        return True, "free"

    if spend_coin(telegram_id):
        return True, "coin"

    return False, "none"


async def send_card(update: Update, card_name: str):
    await update.message.reply_text(f"🃏 {card_name}")
    image_path = get_card_image_path(card_name)
    if os.path.exists(image_path):
        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)


async def run_chat_completion(messages: list[dict], model: str, max_tokens: int = 850) -> str:
    def _call():
        return ai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.8,
            max_tokens=max_tokens,
        )

    try:
        response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=20)
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("CHAT COMPLETION ERROR:", e)
        raise


async def run_vision_completion(prompt: str, image_url: str) -> str:
    def _call():
        return ai_client.responses.create(
            model=GROQ_VISION_MODEL,
            input=[
                {"role": "system", "content": current_system_prompt(SERVICE_PHOTO)},
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "detail": "auto", "image_url": image_url},
                    ],
                },
            ],
        )

    try:
        response = await asyncio.wait_for(asyncio.to_thread(_call), timeout=25)
        return response.output_text.strip()
    except Exception as e:
        print("VISION COMPLETION ERROR:", e)
        raise


async def generate_tarot_answer(name: str, birthdate: str, question: str, cards: list[str], history: list[tuple[str, str]]) -> str:
    cards_text = ", ".join(cards)
    user_prompt = (
        f"Имя: {name}\n"
        f"Дата рождения: {birthdate}\n"
        f"Вопрос: {question}\n"
        f"Карты: {cards_text}\n\n"
        "Сделай индивидуальный расклад в структуре:\n"
        "1. Короткое вступление от имени Марии\n"
        "2. Прошлое\n"
        "3. Настоящее\n"
        "4. Будущее\n"
        "5. Что важно сейчас\n"
    )

    messages = [{"role": "system", "content": current_system_prompt(SERVICE_TAROT)}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    return await run_chat_completion(messages, GROQ_TEXT_MODEL)


async def generate_astro_answer(name: str, birthdate: str, question: str, history: list[tuple[str, str]]) -> str:
    user_prompt = (
        f"Имя: {name}\n"
        f"Дата рождения: {birthdate}\n"
        f"Запрос: {question}\n\n"
        "Сделай астрологический интуитивный разбор: характер, текущий период, сильные стороны, риски, и 'Что важно сейчас'."
    )

    messages = [{"role": "system", "content": current_system_prompt(SERVICE_ASTRO)}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    return await run_chat_completion(messages, GROQ_TEXT_MODEL)


async def generate_natal_answer(name: str, birthdate: str, extra: str, question: str, history: list[tuple[str, str]]) -> str:
    user_prompt = (
        f"Имя: {name}\n"
        f"Дата рождения: {birthdate}\n"
        f"Время и место рождения: {extra}\n"
        f"Запрос: {question}\n\n"
        "Сделай мягкий разбор натальной карты в свободной форме. "
        "Если данных недостаточно для точной карты, честно скажи, что это интуитивная интерпретация. "
        "В конце обязательно дай блок 'Что важно сейчас'."
    )

    messages = [{"role": "system", "content": current_system_prompt(SERVICE_NATAL)}]
    for role, content in history:
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_prompt})

    return await run_chat_completion(messages, GROQ_TEXT_MODEL)


async def generate_photo_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, birthdate: str, question: str) -> str:
    if "photo_file_id" not in context.user_data:
        raise ValueError("Фото не найдено")

    tg_file = await context.bot.get_file(context.user_data["photo_file_id"])
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{tg_file.file_path}"

    prompt = (
        f"Имя: {name}\n"
        f"Дата рождения: {birthdate}\n"
        f"Запрос: {question}\n\n"
        "Посмотри на фото. Опиши мягко визуальное впечатление, эмоциональный фон, "
        "личную энергетику и заверши блоком 'Что важно сейчас'. "
        "Не утверждай жёстко то, чего нельзя надёжно знать. Пиши бережно."
    )

    return await run_vision_completion(prompt, file_url)


async def generate_followup_answer(telegram_id: int, service_type: str, followup_text: str) -> str:
    history = get_recent_messages(telegram_id, service_type, limit=12)

    messages = [{"role": "system", "content": current_system_prompt(service_type)}]

    for role, content in history:
        messages.append({"role": role, "content": content})

    messages.append(
        {
            "role": "user",
            "content": (
                f"Это уточняющий вопрос по прошлому разбору: {followup_text}\n\n"
                "Ответь мягко, по-человечески, от имени Марии в женском роде. "
                "Не повторяй весь прошлый расклад заново. "
                "Дай именно уточнение и закончи блоком 'Что важно сейчас'."
            ),
        }
    )

    return await run_chat_completion(messages, GROQ_TEXT_MODEL, max_tokens=500)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("UNHANDLED ERROR:", context.error)

    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Во время ответа произошла ошибка. Попробуй ещё раз.",
                reply_markup=MAIN_MENU
            )
    except Exception as e:
        print("ERROR HANDLER FAILED:", e)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🔮 Привет. Я Мария.\n\n"
        "Я готова помочь тебе с таро, астрологическим разбором, "
        "интуитивной натальной картой и анализом по фото.\n\n"
        "Выбери, что тебе нужно:",
        reply_markup=MAIN_MENU,
    )
    return ConversationHandler.END


async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Что умеет бот:\n\n"
        "🔮 Таро — расклад на 3 карты\n"
        "🌙 Астрология — интуитивный разбор по дате рождения\n"
        "🪐 Натальная карта — мягкий ИИ-разбор по данным рождения\n"
        "📷 Анализ по фото — визуально-интуитивный разбор\n"
        "✨ Уточнить ответ — продолжение диалога по текущему разбору\n\n"
        "После 3 бесплатных услуг используется 1 монета.",
        reply_markup=MAIN_MENU,
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    coins = get_coins_balance(telegram_id)
    used = get_free_readings_used(telegram_id)
    left = max(0, 3 - used)
    await update.message.reply_text(
        f"🪙 Монет: {coins}\n"
        f"🎁 Бесплатных услуг осталось: {left}\n"
        f"1 монета = 1 услуга",
        reply_markup=MAIN_MENU,
    )


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    rows = get_user_readings(telegram_id, limit=5)
    if not rows:
        await update.message.reply_text("📜 У тебя пока нет сохранённых разборов.", reply_markup=MAIN_MENU)
        return

    parts = ["📜 Последние разборы:\n"]
    for i, (service_type, question, cards, created_at) in enumerate(rows, start=1):
        parts.append(
            f"{i}. {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"Услуга: {get_service_label(service_type)}\n"
            f"Запрос: {question}\n"
            f"{'Карты: ' + cards if cards else ''}\n"
        )

    await update.message.reply_text("\n".join(parts), reply_markup=MAIN_MENU)


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("1 монета — 25 ⭐", callback_data="buy_coins_1")],
        [InlineKeyboardButton("5 монет — 99 ⭐", callback_data="buy_coins_5")],
        [InlineKeyboardButton("12 монет — 199 ⭐", callback_data="buy_coins_12")],
        [InlineKeyboardButton("25 монет — 399 ⭐", callback_data="buy_coins_25")],
    ])
    await update.message.reply_text("⭐ Выбери пакет монет:", reply_markup=keyboard)


async def send_stars_invoice(update: Update, package_key: str):
    package = COIN_PACKAGES[package_key]
    await update.message.reply_invoice(
        title=package["title"],
        description=f"{package['coins']} монет для услуг Марии",
        payload=package_key,
        currency="XTR",
        prices=[LabeledPrice(label=package["title"], amount=package["stars"])],
        provider_token="",
        start_parameter=package_key,
    )


async def buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    mapping = {
        "buy_coins_1": "coins_1",
        "buy_coins_5": "coins_5",
        "buy_coins_12": "coins_12",
        "buy_coins_25": "coins_25",
    }
    package_key = mapping.get(query.data)
    if not package_key:
        await query.message.reply_text("❌ Неизвестный пакет.")
        return

    package = COIN_PACKAGES[package_key]
    await query.message.reply_invoice(
        title=package["title"],
        description=f"{package['coins']} монет для услуг Марии",
        payload=package_key,
        currency="XTR",
        prices=[LabeledPrice(label=package["title"], amount=package["stars"])],
        provider_token="",
        start_parameter=package_key,
    )


async def buy1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(update, "coins_1")


async def buy5(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(update, "coins_5")


async def buy12(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(update, "coins_12")


async def buy25(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_stars_invoice(update, "coins_25")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    telegram_id = update.effective_user.id

    package_key = payment.invoice_payload
    package = COIN_PACKAGES.get(package_key)

    if not package:
        await update.message.reply_text("❌ Ошибка пакета оплаты.", reply_markup=MAIN_MENU)
        return

    add_coins(telegram_id, package["coins"])
    save_payment(
        telegram_id=telegram_id,
        package_name=package["title"],
        coins_amount=package["coins"],
        stars_amount=package["stars"],
        charge_id=payment.telegram_payment_charge_id,
    )

    balance_now = get_coins_balance(telegram_id)
    await update.message.reply_text(
        f"✅ Оплата прошла успешно.\n"
        f"Начислено монет: {package['coins']}\n"
        f"🪙 Текущий баланс: {balance_now}",
        reply_markup=MAIN_MENU,
    )


async def begin_service(update: Update, context: ContextTypes.DEFAULT_TYPE, service_type: str):
    context.user_data.clear()
    context.user_data["service_type"] = service_type

    labels = {
        SERVICE_TAROT: "🔮 Таро",
        SERVICE_ASTRO: "🌙 Астрология",
        SERVICE_NATAL: "🪐 Натальная карта",
        SERVICE_PHOTO: "📷 Анализ по фото",
    }

    await update.message.reply_text(
        f"{labels[service_type]}\n\nНапиши своё имя.",
        reply_markup=MAIN_MENU,
    )
    return ASK_NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()

    if not is_valid_name(name):
        await update.message.reply_text(
            "❗️Похоже, это не имя. Пожалуйста, введи имя буквами.",
            reply_markup=MAIN_MENU
        )
        return ASK_NAME

    context.user_data["name"] = name
    await update.message.reply_text(
        "📅 Теперь отправь дату рождения в формате ДД.ММ.ГГГГ",
        reply_markup=MAIN_MENU
    )
    return ASK_BIRTHDATE


async def get_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    birthdate = update.message.text.strip()

    if not is_valid_birthdate(birthdate):
        await update.message.reply_text(
            "❗️Дата введена неверно. Введи дату в формате ДД.ММ.ГГГГ, например 17.05.1998",
            reply_markup=MAIN_MENU
        )
        return ASK_BIRTHDATE

    context.user_data["birthdate"] = birthdate

    telegram_id = update.effective_user.id
    create_or_update_user(
        telegram_id=telegram_id,
        name=context.user_data["name"],
        birthdate=birthdate
    )

    service_type = context.user_data["service_type"]

    if service_type == SERVICE_NATAL:
        await update.message.reply_text(
            "🕰️ Теперь напиши время и место рождения одним сообщением.\n"
            "Например: 14:35, Москва",
            reply_markup=MAIN_MENU
        )
        return ASK_EXTRA

    await update.message.reply_text(
        "💭 Напиши вопрос или тему, которая тебя волнует.",
        reply_markup=MAIN_MENU
    )
    return ASK_QUESTION


async def get_extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["extra"] = update.message.text.strip()
    await update.message.reply_text(
        "💭 Теперь напиши свой вопрос или тему, которую хочешь разобрать.",
        reply_markup=MAIN_MENU
    )
    return ASK_QUESTION


async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["question"] = update.message.text.strip()
    service_type = context.user_data["service_type"]

    if service_type == SERVICE_PHOTO:
        await update.message.reply_text(
            "📷 Теперь отправь одно фото человека.",
            reply_markup=PHOTO_MENU
        )
        return ASK_PHOTO

    await update.message.reply_text(
        "📸 Если хочешь, отправь фото для дополнительного настроя.\n"
        "Если не хочешь — нажми «📷 Пропустить фото».",
        reply_markup=PHOTO_MENU
    )
    return ASK_PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    context.user_data["photo_file_id"] = photo.file_id
    return await process_service(update, context)


async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("photo_file_id", None)
    return await process_service(update, context)


async def process_service(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    service_type = context.user_data["service_type"]
    name = context.user_data["name"]
    birthdate = context.user_data["birthdate"]
    question = context.user_data["question"]
    extra = context.user_data.get("extra", "")

    allowed, source = ensure_paid_or_free(telegram_id)
    if not allowed:
        await update.message.reply_text(
            "💳 Бесплатные услуги закончились, а монет не осталось.\n"
            "Проверь баланс или пополни счёт.",
            reply_markup=MAIN_MENU
        )
        return ConversationHandler.END

    await update.message.reply_text("✨ Я настраиваюсь на тебя...")
    await asyncio.sleep(0.6)
    await update.message.reply_text("🕯️ Собираю ответ Марии...")
    await asyncio.sleep(0.6)

    history = get_recent_messages(telegram_id, service_type, limit=8)
    cards = []
    cards_text = None

    try:
        if service_type == SERVICE_TAROT:
            cards = random.sample(TAROT_CARDS, 3)
            cards_text = ", ".join(cards)

            await update.message.reply_text("🃏 Я вытягиваю для тебя 3 карты...")
            await asyncio.sleep(0.7)
            for idx, card in enumerate(cards, start=1):
                await update.message.reply_text(f"Карта {idx}:")
                await send_card(update, card)
                await asyncio.sleep(0.4)

            answer = await generate_tarot_answer(name, birthdate, question, cards, history)

        elif service_type == SERVICE_ASTRO:
            answer = await generate_astro_answer(name, birthdate, question, history)

        elif service_type == SERVICE_NATAL:
            answer = await generate_natal_answer(name, birthdate, extra, question, history)

        elif service_type == SERVICE_PHOTO:
            answer = await generate_photo_answer(update, context, name, birthdate, question)

        else:
            answer = "⚠️ Неизвестный режим."
    except Exception as e:
        print("AI ERROR:", e)

        if service_type == SERVICE_TAROT:
            answer = (
                f"🔮 {name}, я увидела твой расклад и уже могу мягко подсветить главное.\n\n"
                f"Выпавшие карты: {cards_text or 'не определены'}.\n\n"
                f"Сейчас в твоей ситуации есть тема созревания, внутренней подготовки и выхода к более устойчивому этапу. "
                f"Ответ на вопрос «{question}» не выглядит как мгновенный рывок, но карты показывают, что движение идёт.\n\n"
                f"Что важно сейчас:\n"
                f"Не дави на события. Твой путь идёт через постепенность, укрепление опоры и зрелое решение."
            )

        elif service_type == SERVICE_ASTRO:
            answer = (
                f"🌙 {name}, я чувствую, что твой текущий период связан с внутренней перенастройкой и ожиданием важного поворота.\n\n"
                f"По твоей дате рождения видно, что тебе сейчас важно не торопить будущее, а выстраивать почву под него.\n\n"
                f"Что важно сейчас:\n"
                f"Собери внутреннюю опору и не пытайся вытянуть ответ силой."
            )

        elif service_type == SERVICE_NATAL:
            answer = (
                f"🪐 {name}, я сейчас не смогла углубить натальный разбор через ИИ, "
                f"но по твоим данным чувствуется сильная тема судьбоносного взросления и важного личного выбора.\n\n"
                f"Что важно сейчас:\n"
                f"Не сомневайся в своём пути слишком сильно. Сейчас тебе важнее точность и честность с собой."
            )

        elif service_type == SERVICE_PHOTO:
            answer = (
                f"📷 {name}, я не смогла закончить глубокий разбор по фото через ИИ, "
                f"но чувствую, что твой образ сейчас показывает внутреннюю собранность и скрытое напряжение.\n\n"
                f"Что важно сейчас:\n"
                f"Дай себе больше воздуха и не неси всё в одиночку."
            )

        else:
            answer = (
                f"🔮 {name}, я почувствовала твой запрос, но не смогла сейчас завершить глубокий разбор.\n\n"
                f"Что важно сейчас:\n"
                f"Сделай шаг назад, выдохни и вернись к вопросу чуть позже."
            )

    save_reading(
        telegram_id=telegram_id,
        service_type=service_type,
        user_name=name,
        birthdate=birthdate,
        question=question,
        cards=cards_text,
        answer=answer,
    )
    save_message(telegram_id, service_type, "user", question)
    save_message(telegram_id, service_type, "assistant", answer)

    left = max(0, 3 - get_free_readings_used(telegram_id))
    coins_now = get_coins_balance(telegram_id)

    await update.message.reply_text(answer, reply_markup=FOLLOWUP_MENU)
    await update.message.reply_text(
        f"🎁 Бесплатных услуг осталось: {left}\n"
        f"🪙 Монет: {coins_now}\n\n"
        f"Ты можешь сразу написать уточняющий вопрос по этому разбору.",
        reply_markup=FOLLOWUP_MENU
    )
    context.user_data["followup_enabled"] = True
    return FOLLOWUP


async def ask_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("service_type"):
        await update.message.reply_text(
            "Сначала выбери услугу и получи разбор.",
            reply_markup=MAIN_MENU
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "✨ Напиши уточняющий вопрос по последнему ответу Марии.",
        reply_markup=FOLLOWUP_MENU
    )
    return FOLLOWUP


async def handle_followup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    service_type = context.user_data.get("service_type")

    if not service_type:
        await update.message.reply_text(
            "Сначала получи основной разбор.",
            reply_markup=MAIN_MENU
        )
        return ConversationHandler.END

    followup_text = update.message.text.strip()

    await update.message.reply_text("✨ Я уточняю твой прошлый разбор...")

    try:
        save_message(telegram_id, service_type, "user", followup_text)

        answer = await generate_followup_answer(
            telegram_id=telegram_id,
            service_type=service_type,
            followup_text=followup_text
        )

        save_message(telegram_id, service_type, "assistant", answer)

        await update.message.reply_text(answer, reply_markup=FOLLOWUP_MENU)
        return FOLLOWUP

    except Exception as e:
        print("FOLLOWUP ERROR:", e)

        fallback_answer = (
            "Я почувствовала твой уточняющий вопрос.\n\n"
            f"Ты спросил: {followup_text}\n\n"
            "Сейчас я бы советовала не искать мгновенный ответ, а посмотреть, "
            "какой маленький шаг ты можешь сделать уже сегодня.\n\n"
            "Что важно сейчас:\n"
            "Сосредоточься не на страхе будущего, а на ближайшем понятном действии."
        )

        await update.message.reply_text(fallback_answer, reply_markup=FOLLOWUP_MENU)
        return FOLLOWUP


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🔮 Таро":
        return await begin_service(update, context, SERVICE_TAROT)

    if text == "🌙 Астрология":
        return await begin_service(update, context, SERVICE_ASTRO)

    if text == "🪐 Натальная карта":
        return await begin_service(update, context, SERVICE_NATAL)

    if text == "📷 Анализ по фото":
        return await begin_service(update, context, SERVICE_PHOTO)

    if text == "🪙 Баланс":
        await balance(update, context)
        return ConversationHandler.END

    if text == "⭐ Купить монеты":
        await buy(update, context)
        return ConversationHandler.END

    if text == "📜 История":
        await show_history(update, context)
        return ConversationHandler.END

    if text == "ℹ️ Помощь":
        await help_menu(update, context)
        return ConversationHandler.END

    if text == "📷 Пропустить фото":
        return await skip_photo(update, context)

    if text == "✨ Уточнить ответ":
        return await ask_followup(update, context)

    await update.message.reply_text("Выбери действие кнопками ниже.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Хорошо, остановимся здесь.", reply_markup=MAIN_MENU)
    return ConversationHandler.END


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    menu_pattern = r"^(🔮 Таро|🌙 Астрология|🪐 Натальная карта|📷 Анализ по фото|🪙 Баланс|⭐ Купить монеты|📜 История|ℹ️ Помощь|✨ Уточнить ответ)$"
    photo_menu_pattern = r"^(📷 Пропустить фото|🔮 Таро|🌙 Астрология|🪐 Натальная карта|📷 Анализ по фото|🪙 Баланс|⭐ Купить монеты|📜 История|ℹ️ Помощь|✨ Уточнить ответ)$"

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex(r"^🔮 Таро$"), menu_router),
            MessageHandler(filters.Regex(r"^🌙 Астрология$"), menu_router),
            MessageHandler(filters.Regex(r"^🪐 Натальная карта$"), menu_router),
            MessageHandler(filters.Regex(r"^📷 Анализ по фото$"), menu_router),
        ],
        states={
            ASK_NAME: [
                MessageHandler(filters.Regex(menu_pattern), menu_router),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_name),
            ],
            ASK_BIRTHDATE: [
                MessageHandler(filters.Regex(menu_pattern), menu_router),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_birthdate),
            ],
            ASK_EXTRA: [
                MessageHandler(filters.Regex(menu_pattern), menu_router),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_extra),
            ],
            ASK_QUESTION: [
                MessageHandler(filters.Regex(menu_pattern), menu_router),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_question),
            ],
            ASK_PHOTO: [
                MessageHandler(filters.Regex(photo_menu_pattern), menu_router),
                MessageHandler(filters.PHOTO, get_photo),
            ],
            FOLLOWUP: [
                MessageHandler(filters.Regex(menu_pattern), menu_router),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_followup),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("help", help_menu))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("buy1", buy1))
    app.add_handler(CommandHandler("buy5", buy5))
    app.add_handler(CommandHandler("buy12", buy12))
    app.add_handler(CommandHandler("buy25", buy25))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern=r"^buy_coins_"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(MessageHandler(filters.Regex(menu_pattern), menu_router))
    app.add_handler(MessageHandler(filters.Regex(r"^📷 Пропустить фото$"), menu_router))

    app.add_error_handler(error_handler)

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
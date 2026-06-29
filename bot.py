import asyncio
import os

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from dotenv import load_dotenv

from services.client import Client

# ==========================================
# CONFIG
# ==========================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# CLIENT
# ==========================================

cli = Client()

# Cache de grupos
AVAILABLE_GROUPS = set(cli.getGroups())

# ==========================================
# TEMP STORAGE
# Luego reemplazar por DB
# ==========================================

user_groups = {}

# Usuarios esperando input del grupo
waiting_for_group = set()

# ==========================================
# MAIN MENU
# ==========================================


def get_main_menu():

    builder = ReplyKeyboardBuilder()

    builder.add(types.KeyboardButton(text="📅 Расписание"))
    builder.add(types.KeyboardButton(text="⏳ Дедлайны"))
    builder.add(types.KeyboardButton(text="📊 Мои оценки"))
    builder.add(types.KeyboardButton(text="✨ Отзывы и Мемы"))

    builder.adjust(2, 2)

    return builder.as_markup(resize_keyboard=True)

# ==========================================
# START
# ==========================================


@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    user_id = message.from_user.id

    # Usuario ya tiene grupo
    if user_id in user_groups:

        await message.answer(
            f"✅ Ваша группа: {user_groups[user_id]}",
            reply_markup=get_main_menu()
        )

        return

    # Esperar input grupo
    waiting_for_group.add(user_id)

    await message.answer(
        "📚 Введите номер вашей группы:\n\n"
        "Например:\n"
        "12002308"
    )

# ==========================================
# CHANGE GROUP
# ==========================================


@dp.message(Command("changegroup"))
async def change_group(message: types.Message):

    user_id = message.from_user.id

    waiting_for_group.add(user_id)

    await message.answer(
        "✏️ Введите новый номер группы:"
    )

# ==========================================
# SCHEDULE
# ==========================================


@dp.message(F.text == "📅 Расписание")
async def show_schedule(message: types.Message):

    user_id = message.from_user.id

    group = user_groups.get(user_id)

    if not group:

        await message.answer(
            "⚠️ Сначала выберите группу через /start"
        )

        return

    # ==========================================
    # LOADING MESSAGE
    # ==========================================

    loading_message = await message.answer(
        "⏳ Загружаю расписание..."
    )

    # ==========================================
    # CURRENT WEEK
    # ==========================================

    today = datetime.now()

    # Monday
    start_of_week = today - timedelta(days=today.weekday())

    # Sunday
    end_of_week = start_of_week + timedelta(days=6)

    fecha_desde = start_of_week.strftime("%d%m%Y")
    fecha_hasta = end_of_week.strftime("%d%m%Y")

    # ==========================================
    # GET SCHEDULE
    # ==========================================

    try:

        schedule = cli.getRaspisanie(
            group,
            fecha_desde,
            fecha_hasta
        )

    except Exception as e:

        await loading_message.edit_text(
            f"❌ Ошибка получения расписания\n\n{e}"
        )

        return

    # ==========================================
    # BUILD MESSAGE
    # ==========================================

    text = (
        f"📅 Расписание группы {group}\n"
        f"📆 {start_of_week.strftime('%d.%m')} - "
        f"{end_of_week.strftime('%d.%m.%Y')}\n\n"
    )

    if not schedule:

        text += "❌ Нет расписания"

        await loading_message.edit_text(text)

        return

    for day in schedule:

        text += f"📌 <b>{day}</b>\n\n"

        lessons = schedule[day]

        if not lessons:

            text += "🏖 Выходной\n\n"
            continue

        for lesson in lessons:

            numero = lesson.get("numero", "")
            horario = lesson.get("horario", "")
            tipo = lesson.get("tipo", "")
            materia = lesson.get("materia", "")

            text += (
                f"🔹 <b>{numero}</b>\n"
                f"🕒 {horario}\n"
                f"📘 {materia}\n"
                f"📖 {tipo}\n\n"
            )

    # ==========================================
    # INLINE BUTTONS
    # ==========================================

    builder = InlineKeyboardBuilder()

    builder.add(
        types.InlineKeyboardButton(
            text="🔄 Обновить",
            callback_data="refresh_schedule"
        )
    )

    builder.adjust(1)

    # ==========================================
    # SEND
    # ==========================================

    await loading_message.edit_text(
        text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )

# ==========================================
# DEADLINES
# ==========================================


@dp.message(F.text == "⏳ Дедлайны")
async def show_deadlines(message: types.Message):

    builder = InlineKeyboardBuilder()

    builder.add(
        types.InlineKeyboardButton(
            text="➕ Добавить задачу",
            callback_data="dead_add"
        )
    )

    builder.add(
        types.InlineKeyboardButton(
            text="⚙️ Настроить напоминания",
            callback_data="dead_settings"
        )
    )

    builder.adjust(1, 1)

    await message.answer(
        "⏳ Твои дедлайны:",
        reply_markup=builder.as_markup()
    )

# ==========================================
# GRADES
# ==========================================


@dp.message(F.text == "📊 Мои оценки")
async def show_grades(message: types.Message):

    builder = InlineKeyboardBuilder()

    builder.add(
        types.InlineKeyboardButton(
            text="🔄 Обновить баллы",
            callback_data="grades_refresh"
        )
    )

    builder.adjust(1)

    await message.answer(
        "📊 Твои оценки:",
        reply_markup=builder.as_markup()
    )

# ==========================================
# MEMES / REVIEWS
# ==========================================


@dp.message(F.text == "✨ Отзывы и Мемы")
async def show_fun_features(message: types.Message):

    builder = InlineKeyboardBuilder()

    builder.add(
        types.InlineKeyboardButton(
            text="🤡 Прислать мем",
            callback_data="fun_meme"
        )
    )

    builder.add(
        types.InlineKeyboardButton(
            text="✍️ Оставить отзыв",
            callback_data="fun_review"
        )
    )

    builder.adjust(1, 1)

    await message.answer(
        "✨ Раздел мемов и отзывов",
        reply_markup=builder.as_markup()
    )

# ==========================================
# CALLBACKS
# ==========================================


@dp.callback_query(F.data == "refresh_schedule")
async def refresh_schedule(callback: types.CallbackQuery):

    await callback.answer(
        "🔄 Расписание обновлено"
    )


@dp.callback_query(F.data == "dead_add")
async def dead_add(callback: types.CallbackQuery):

    await callback.answer(
        "➕ Добавление задачи"
    )


@dp.callback_query(F.data == "dead_settings")
async def dead_settings(callback: types.CallbackQuery):

    await callback.answer(
        "⚙️ Настройки уведомлений"
    )


@dp.callback_query(F.data == "grades_refresh")
async def grades_refresh(callback: types.CallbackQuery):

    await callback.answer(
        "🔄 Баллы обновлены"
    )


@dp.callback_query(F.data == "fun_meme")
async def fun_meme(callback: types.CallbackQuery):

    await callback.answer(
        "🤡 Мемы скоро будут"
    )


@dp.callback_query(F.data == "fun_review")
async def fun_review(callback: types.CallbackQuery):

    await callback.answer(
        "✍️ Отзывы скоро будут"
    )

# ==========================================
# HANDLE GROUP INPUT
# SIEMPRE AL FINAL
# ==========================================


@dp.message()
async def handle_group_input(message: types.Message):

    user_id = message.from_user.id

    # Usuario NO está вводит группу
    if user_id not in waiting_for_group:
        return

    group = message.text.strip()

    # Validación grupo
    if group not in AVAILABLE_GROUPS:

        await message.answer(
            "❌ Группа не найдена.\n\n"
            "Попробуйте еще раз."
        )

        return

    # Guardar grupo
    user_groups[user_id] = group

    # Salir modo input
    waiting_for_group.remove(user_id)

    await message.answer(
        f"✅ Группа сохранена: {group}",
        reply_markup=get_main_menu()
    )

# ==========================================
# MAIN
# ==========================================


async def main():

    print("Bot started...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
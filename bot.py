import asyncio
import os

from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from dotenv import load_dotenv

from services.client import Client
from services.database import (
    init_db, get_or_create_user, set_user_group, get_user_group,
    add_deadline, get_deadlines, mark_deadline_done,
    get_reminder_settings, toggle_reminders,
    add_review, get_reviews
)

# ==========================================
# CONFIG
# ==========================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# DATABASE
# ==========================================

init_db()

# ==========================================
# CLIENT
# ==========================================

cli = Client()

AVAILABLE_GROUPS = set(cli.getGroups())

# ==========================================
# SESSION STATE (только временные флаги, не данные)
# ==========================================

waiting_for_group = set()
waiting_for_deadline_title = {}   # user_id -> True
waiting_for_deadline_date = {}    # user_id -> title
waiting_for_review_teacher = set()
waiting_for_review_text = {}      # user_id -> teacher

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
    get_or_create_user(user_id)

    group = get_user_group(user_id)

    if group:
        await message.answer(
            f"✅ Ваша группа: {group}",
            reply_markup=get_main_menu()
        )
        return

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
    await message.answer("✏️ Введите новый номер группы:")

# ==========================================
# SCHEDULE
# ==========================================


@dp.message(F.text == "📅 Расписание")
async def show_schedule(message: types.Message):
    user_id = message.from_user.id
    group = get_user_group(user_id)

    if not group:
        await message.answer("⚠️ Сначала выберите группу через /start")
        return

    loading_message = await message.answer("⏳ Загружаю расписание...")

    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    fecha_desde = start_of_week.strftime("%d%m%Y")
    fecha_hasta = end_of_week.strftime("%d%m%Y")

    try:
        schedule = cli.getRaspisanie(group, fecha_desde, fecha_hasta)
    except Exception as e:
        await loading_message.edit_text(f"❌ Ошибка получения расписания\n\n{e}")
        return

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

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_schedule"))
    builder.adjust(1)

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
    user_id = message.from_user.id
    deadlines = get_deadlines(user_id)

    if not deadlines:
        text = "⏳ У тебя пока нет дедлайнов."
    else:
        text = "⏳ Твои дедлайны:\n\n"
        for d in deadlines:
            due = datetime.fromisoformat(d["due_date"]).strftime("%d.%m.%Y")
            text += f"🔸 <b>{d['title']}</b>\n📆 {due}\n"
            if d["description"]:
                text += f"📝 {d['description']}\n"
            text += f"✅ /done_{d['id']}\n\n"

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="➕ Добавить задачу", callback_data="dead_add"))
    builder.add(types.InlineKeyboardButton(text="⚙️ Настроить напоминания", callback_data="dead_settings"))
    builder.adjust(1, 1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


@dp.message(F.text.startswith("/done_"))
async def done_deadline(message: types.Message):
    try:
        deadline_id = int(message.text.split("_")[1])
    except (IndexError, ValueError):
        await message.answer("❌ Неверный формат команды")
        return

    mark_deadline_done(deadline_id)
    await message.answer("✅ Задача отмечена выполненной")

# ==========================================
# GRADES
# ==========================================


@dp.message(F.text == "📊 Мои оценки")
async def show_grades(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔄 Обновить баллы", callback_data="grades_refresh"))
    builder.adjust(1)

    await message.answer("📊 Твои оценки:", reply_markup=builder.as_markup())

# ==========================================
# MEMES / REVIEWS
# ==========================================


@dp.message(F.text == "✨ Отзывы и Мемы")
async def show_fun_features(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🤡 Прислать мем", callback_data="fun_meme"))
    builder.add(types.InlineKeyboardButton(text="✍️ Оставить отзыв", callback_data="fun_review"))
    builder.add(types.InlineKeyboardButton(text="📖 Читать отзывы", callback_data="fun_read_reviews"))
    builder.adjust(1, 1, 1)

    await message.answer("✨ Раздел мемов и отзывов", reply_markup=builder.as_markup())

# ==========================================
# CALLBACKS
# ==========================================


@dp.callback_query(F.data == "refresh_schedule")
async def refresh_schedule(callback: types.CallbackQuery):
    await callback.answer("🔄 Расписание обновлено")


@dp.callback_query(F.data == "dead_add")
async def dead_add(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    waiting_for_deadline_title[user_id] = True
    await callback.message.answer("📝 Введите название задачи:")
    await callback.answer()


@dp.callback_query(F.data == "dead_settings")
async def dead_settings(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    settings = get_reminder_settings(user_id)
    status = "включены ✅" if settings["enabled"] else "выключены ❌"

    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="🔔 Вкл/Выкл напоминания", callback_data="toggle_reminders"))
    builder.adjust(1)

    await callback.message.answer(
        f"⚙️ Напоминания: {status}\n"
        f"⏰ За {settings['hours_before']}ч до дедлайна",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "toggle_reminders")
async def toggle_reminders_cb(callback: types.CallbackQuery):
    new_value = toggle_reminders(callback.from_user.id)
    text = "🔔 Напоминания включены" if new_value else "🔕 Напоминания выключены"
    await callback.answer(text)


@dp.callback_query(F.data == "grades_refresh")
async def grades_refresh(callback: types.CallbackQuery):
    await callback.answer("🔄 Баллы обновлены")


@dp.callback_query(F.data == "fun_meme")
async def fun_meme(callback: types.CallbackQuery):
    await callback.answer("🤡 Мемы скоро будут")


@dp.callback_query(F.data == "fun_review")
async def fun_review(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    waiting_for_review_teacher.add(user_id)
    await callback.message.answer("👤 Укажите имя преподавателя:")
    await callback.answer()


@dp.callback_query(F.data == "fun_read_reviews")
async def fun_read_reviews(callback: types.CallbackQuery):
    reviews = get_reviews()

    if not reviews:
        await callback.message.answer("📭 Отзывов пока нет.")
        await callback.answer()
        return

    text = "📖 Последние отзывы:\n\n"
    for r in reviews[:10]:
        rating = f" ({r['rating']}/5)" if r["rating"] else ""
        text += f"👤 <b>{r['teacher']}</b>{rating}\n💬 {r['text']}\n\n"

    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# ==========================================
# HANDLE TEXT INPUT (группа / дедлайны / отзывы)
# SIEMPRE AL FINAL
# ==========================================


@dp.message()
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip() if message.text else ""

    # ---- Дедлайн: шаг 1, название ----
    if user_id in waiting_for_deadline_title:
        del waiting_for_deadline_title[user_id]
        waiting_for_deadline_date[user_id] = text
        await message.answer("📆 Теперь введите дату дедлайна (формат: ДД.ММ.ГГГГ):")
        return

    # ---- Дедлайн: шаг 2, дата ----
    if user_id in waiting_for_deadline_date:
        title = waiting_for_deadline_date[user_id]

        try:
            due_date = datetime.strptime(text, "%d.%m.%Y").isoformat()
        except ValueError:
            await message.answer("❌ Неверный формат даты. Попробуй ещё раз: ДД.ММ.ГГГГ")
            return

        del waiting_for_deadline_date[user_id]
        add_deadline(user_id, title, due_date)
        await message.answer(f"✅ Дедлайн «{title}» добавлен!")
        return

    # ---- Отзыв: шаг 1, имя преподавателя ----
    if user_id in waiting_for_review_teacher:
        waiting_for_review_teacher.remove(user_id)
        waiting_for_review_text[user_id] = text
        await message.answer("✍️ Теперь напишите текст отзыва:")
        return

    # ---- Отзыв: шаг 2, текст отзыва ----
    if user_id in waiting_for_review_text:
        teacher = waiting_for_review_text.pop(user_id)
        add_review(teacher, text)
        await message.answer("✅ Спасибо! Отзыв сохранён анонимно.")
        return

    # ---- Группа ----
    if user_id not in waiting_for_group:
        return

    group = text

    if group not in AVAILABLE_GROUPS:
        await message.answer(
            "❌ Группа не найдена.\n\n"
            "Попробуйте еще раз."
        )
        return

    set_user_group(user_id, group)
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

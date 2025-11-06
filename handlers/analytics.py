from datetime import datetime, timedelta
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.admins import has_admin_panel, is_admin
from config.challenges import get_all_challenges, get_challenge
from database import (
    accept_challenge,
    decline_challenge,
    get_accepted_challenges,
    get_reviewed_challenges,
    get_submitted_challenges,
    get_user_challenge_statuses,
    get_user_awarded_points,
    get_user_review_summary,
    mark_challenge_submitted,
)
from keyboards.all_keyboards import (
    get_back_button,
    get_challenge_actions_keyboard,
    get_main_menu,
    get_report_challenges_keyboard,
    get_report_confirmation_keyboard,
    get_tasks_keyboard,
)
from utils.admin_panel import send_admin_panel_prompt

router = Router()

# Временное хранилище выбранных заданий для отчёта
pending_reports: dict[int, str] = {}
# Временное хранилище данных отправленного файла до подтверждения
pending_report_payloads: dict[int, tuple[str, str | None, str, str | None]] = {}


@router.message(Command("admin"))
async def show_admin_panel(message: Message):
    """Показать кнопку админ-панели по запросу."""
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer("Эта команда доступна только администраторам.")
        return
    if not has_admin_panel():
        await message.answer("Админ-панель пока не настроена.")
        return
    await send_admin_panel_prompt(message, user_id)


@router.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message):
    """Возврат в главное меню."""
    await message.answer(
        "🏠 Вы вернулись в главное меню.\nВыберите действие:",
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "📋 Задания")
async def show_tasks(message: Message):
    """Показать список доступных заданий."""
    user_id = message.from_user.id
    challenges = get_all_challenges()
    statuses = get_user_challenge_statuses(user_id)

    available: list[tuple[str, str]] = []
    for challenge_id, data in challenges.items():
        if statuses.get(challenge_id) is None:
            available.append((challenge_id, f"{data['title']} ({data['points']})"))

    accepted = [cid for cid, status in statuses.items() if status == "accepted"]
    submitted = [cid for cid, status in statuses.items() if status == "submitted"]

    if available:
        await message.answer_photo(
            photo=FSInputFile("images/tasks_banner.jpg"),
            caption=(
                "📋 <b>Доступные задания:</b>\n\n"
                "Выбери задание, чтобы узнать подробности и начать челлендж."
            ),
            reply_markup=get_tasks_keyboard(available),
        )
        return

    if accepted:
        await message.answer(
            "📋 Ты уже принял все текущие задания.\n"
            "Перейди в 📮 Отчёт, чтобы отправить результаты.",
            reply_markup=get_main_menu(),
        )
        return

    if len(submitted) == len(challenges):
        await message.answer(
            "✅ Ты выполнил все текущие челленджи!\n"
            "Ждите обновление для новых заданий.",
            reply_markup=get_main_menu(),
        )
        return

    await message.answer(
        "Ждите обновление для новых заданий.",
        reply_markup=get_main_menu(),
    )


@router.callback_query(F.data.startswith("challenge_select:"))
async def task_details(callback: CallbackQuery):
    """Показать детали выбранного задания."""
    challenge_id = callback.data.split(":", maxsplit=1)[1]
    challenge = get_challenge(challenge_id)

    if not challenge:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    statuses = get_user_challenge_statuses(callback.from_user.id)
    if statuses.get(challenge_id) is not None:
        await callback.answer("Это задание тебе уже недоступно.", show_alert=True)
        return

    await callback.message.answer(
        f"<b>{challenge['title']}</b>\n\n"
        f"📝 <b>Описание:</b>\n{challenge['description']}\n\n"
        f"🏆 <b>Награда:</b> {challenge['points']}\n"
        f"🌍 <b>Экономия CO₂:</b> {challenge['co2']}\n\n"
        f"Если готов — принимай задание и выполняй!",
        reply_markup=get_challenge_actions_keyboard(challenge_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("challenge_accept:"))
async def accept_task(callback: CallbackQuery):
    """Обработка принятия задания."""
    challenge_id = callback.data.split(":", maxsplit=1)[1]
    user_id = callback.from_user.id
    challenge = get_challenge(challenge_id)

    if not challenge:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    accepted = accept_challenge(user_id, challenge_id)
    await callback.message.edit_reply_markup(reply_markup=None)

    if not accepted:
        await callback.answer("Задание уже было выполнено ранее.", show_alert=True)
        return

    await callback.message.answer(
        f"✅ <b>{challenge['title']}</b>\n"
        "Задание добавлено во вкладку 📮 Отчёт.\n"
        "Когда выполнишь — выбери задание в разделе отчётов и отправь фото.",
        reply_markup=get_back_button(),
    )
    await callback.answer("Задание принято!")


@router.callback_query(F.data.startswith("challenge_decline:"))
async def decline_task(callback: CallbackQuery):
    """Обработка отказа от задания."""
    challenge_id = callback.data.split(":", maxsplit=1)[1]
    await callback.message.edit_reply_markup(reply_markup=None)
    user_id = callback.from_user.id
    decline_challenge(user_id, challenge_id)
    if pending_reports.get(user_id) == challenge_id:
        pending_reports.pop(user_id, None)
        pending_report_payloads.pop(user_id, None)
    await callback.message.answer(
        "Окей, выбери другое задание, когда будешь готов.",
        reply_markup=get_back_button(),
    )
    await callback.answer("Задание не принято")


@router.message(F.text == "📮 Отчёт")
async def show_report_menu(message: Message):
    """Показать задания, по которым ждём отчёты."""
    user_id = message.from_user.id
    accepted_challenges = get_accepted_challenges(user_id)

    if not accepted_challenges:
        pending_reports.pop(user_id, None)
        pending_report_payloads.pop(user_id, None)
        await message.answer(
            "Вы пока не приняли ни одного задания.",
            reply_markup=get_main_menu(),
        )
        return

    challenges = get_all_challenges()
    keyboard_items = [
        (challenge_id, challenges[challenge_id]["title"])
        for challenge_id in accepted_challenges
        if challenge_id in challenges
    ]

    pending_reports.pop(user_id, None)
    pending_report_payloads.pop(user_id, None)
    await message.answer(
        "📮 <b>Ниже задания, которые вы приняли.</b>\n"
        "Выберите челлендж, чтобы отправить отчёт.",
        reply_markup=get_report_challenges_keyboard(keyboard_items),
    )


@router.callback_query(F.data.startswith("challenge_report:"))
async def request_report(callback: CallbackQuery):
    """Запросить отчёт по выбранному заданию."""
    user_id = callback.from_user.id
    challenge_id = callback.data.split(":", maxsplit=1)[1]
    challenge = get_challenge(challenge_id)

    if not challenge:
        await callback.answer("Задание не найдено", show_alert=True)
        return

    accepted_challenges = get_accepted_challenges(user_id)
    if challenge_id not in accepted_challenges:
        await callback.answer("Сначала прими это задание.", show_alert=True)
        return

    pending_reports[user_id] = challenge_id
    pending_report_payloads.pop(user_id, None)
    await callback.message.answer(
        f"📸 Отправьте отчёт по заданию <b>{challenge['title']}</b>.\n"
        "Пришлите фото и, при желании, добавьте описание.",
        reply_markup=get_back_button(),
    )
    await callback.answer("Жду отчёт!")


@router.message(F.photo)
async def handle_photo_report(message: Message):
    """Обработать фото-отчёт от пользователя."""
    user_id = message.from_user.id
    challenge_id = pending_reports.get(user_id)
    if not challenge_id:
        await message.answer(
            "Чтобы отправить отчёт, выберите задание во вкладке 📮 Отчёт.",
            reply_markup=get_main_menu(),
        )
        return

    challenge = get_challenge(challenge_id)
    photo_file_id = message.photo[-1].file_id
    caption = message.caption if message.caption else None
    pending_report_payloads[user_id] = (photo_file_id, caption, "photo", None)

    title_text = escape(challenge["title"]) if challenge else escape(challenge_id)
    if caption:
        caption_text = escape(caption)
    else:
        caption_text = "Описание не указано."

    confirmation_caption = (
        f"<b>{title_text}</b>\n\n"
        f"{caption_text}\n\n"
        "<b>Проверь отчёт перед отправкой.</b>\n"
        "Нажми «Подтвердить отчёт», если всё верно, или «Редактировать отправленное», чтобы изменить."
    )
    await message.answer_photo(
        photo=photo_file_id,
        caption=confirmation_caption,
        reply_markup=get_report_confirmation_keyboard(),
    )


@router.message(F.document)
async def handle_document_report(message: Message):
    """Обработать документ-отчёт от пользователя."""
    user_id = message.from_user.id
    challenge_id = pending_reports.get(user_id)
    if not challenge_id:
        await message.answer(
            "Чтобы отправить отчёт, выберите задание во вкладке 📮 Отчёт.",
            reply_markup=get_main_menu(),
        )
        return

    challenge = get_challenge(challenge_id)
    document_file_id = message.document.file_id
    document_name = message.document.file_name or "Файл"
    caption = message.caption if message.caption else None
    pending_report_payloads[user_id] = (document_file_id, caption, "document", document_name)

    title_text = escape(challenge["title"]) if challenge else escape(challenge_id)
    if caption:
        caption_text = escape(caption)
    else:
        caption_text = "Описание не указано."

    confirmation_caption = (
        f"<b>{title_text}</b>\n\n"
        f"{caption_text}\n\n"
        "<b>Проверь отчёт перед отправкой.</b>\n"
        "Нажми «Подтвердить отчёт», если всё верно, или «Редактировать отправленное», чтобы изменить."
    )
    await message.answer_document(
        document=document_file_id,
        caption=confirmation_caption,
        reply_markup=get_report_confirmation_keyboard(),
    )


@router.callback_query(F.data == "report_confirm")
async def confirm_report(callback: CallbackQuery):
    """Подтвердить отправку отчёта."""
    user_id = callback.from_user.id
    payload = pending_report_payloads.get(user_id)
    challenge_id = pending_reports.get(user_id)

    if not challenge_id or not payload:
        await callback.answer("Нет отчёта для подтверждения.", show_alert=True)
        return

    file_id, caption, attachment_type, attachment_name = payload
    file_path: str | None = None
    try:
        file_info = await callback.bot.get_file(file_id)
    except Exception:
        file_path = None
    else:
        file_path = file_info.file_path

    submitted = mark_challenge_submitted(
        user_id,
        challenge_id,
        file_id,
        caption,
        attachment_type,
        attachment_name,
        file_path=file_path,
    )
    if not submitted:
        await callback.answer("Не удалось сохранить отчёт. Попробуй отправить снова.", show_alert=True)
        return

    pending_reports.pop(user_id, None)
    pending_report_payloads.pop(user_id, None)
    await callback.message.edit_reply_markup(reply_markup=None)

    challenge = get_challenge(challenge_id)
    title_display = challenge["title"] if challenge else challenge_id
    await callback.message.answer(
        "✅ <b>Отчёт отправлен!</b>\n\n"
        f"Задание: {escape(title_display)}\n"
        "⏳ Отчёт передан на проверку. Статус смотри в разделе 📈 Прогресс.",
        reply_markup=get_main_menu(),
    )
    await callback.answer("Отчёт подтверждён!")


@router.callback_query(F.data == "report_edit")
async def edit_report(callback: CallbackQuery):
    """Вернуться к повторной отправке отчёта."""
    user_id = callback.from_user.id
    challenge_id = pending_reports.get(user_id)
    if not challenge_id:
        await callback.answer("Сначала выбери задание во вкладке 📮 Отчёт.", show_alert=True)
        return

    challenge = get_challenge(challenge_id)
    pending_report_payloads.pop(user_id, None)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(
        f"📸 Отправьте отчёт по заданию <b>{challenge['title']}</b>.\n"
        "Пришлите фото и, при желании, добавьте описание.",
        reply_markup=get_back_button(),
    )
    await callback.answer("Отредактируй и отправь заново.")


@router.message(F.text == "📈 Прогресс")
async def show_progress(message: Message):
    """Показать прогресс пользователя."""
    user_id = message.from_user.id
    accepted = get_accepted_challenges(user_id)
    pending_reports = get_submitted_challenges(user_id, only_pending=True)
    summary = get_user_review_summary(user_id)
    approved_count = summary.get('approved', 0)
    rejected_count = summary.get('rejected', 0)
    pending_count = summary.get('pending', len(pending_reports))

    challenges = get_all_challenges()
    awarded = get_user_awarded_points(user_id)

    def resolve_points_value(challenge_id: str, stored_points: int | None) -> int:
        if stored_points is not None:
            try:
                return int(stored_points)
            except (TypeError, ValueError):
                return 0
        cached = challenges.get(challenge_id)
        details = cached or get_challenge(challenge_id)
        if not details:
            return 0
        value = details.get("points_value")
        if isinstance(value, int):
            return value
        points_field = details.get("points")
        if isinstance(points_field, int):
            return points_field
        if isinstance(points_field, str):
            digits = ''.join(ch for ch in points_field if ch.isdigit())
            if digits:
                try:
                    return int(digits)
                except ValueError:
                    return 0
        return 0

    def get_week_start_msk() -> datetime:
        now_msk = datetime.utcnow() + timedelta(hours=3)
        start_date = now_msk.date() - timedelta(days=now_msk.weekday())
        start_dt = datetime.combine(start_date, datetime.min.time()) + timedelta(minutes=1)
        if now_msk < start_dt:
            start_dt -= timedelta(days=7)
        return start_dt

    week_start = get_week_start_msk()
    total_points = 0
    weekly_points = 0
    for challenge_id, points_value, reviewed_at in awarded:
        points = resolve_points_value(challenge_id, points_value)
        total_points += points
        if reviewed_at:
            try:
                reviewed_dt = datetime.strptime(reviewed_at, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                reviewed_dt = None
            if reviewed_dt and reviewed_dt >= week_start:
                weekly_points += points

    if pending_reports:
        pending_lines = "\n".join(
            f"• {challenges.get(challenge_id, {}).get('title', challenge_id)}"
            for challenge_id, *_ in pending_reports
        )
        pending_text = f"⏳ Отчёты в обработке ({pending_count}):\n{pending_lines}"
    else:
        pending_text = "⏳ Отчёты в обработке: нет"

    await message.answer_photo(
        photo=FSInputFile("images/progress_banner.jpg"),
        caption=(
            "📈 <b>Твой прогресс:</b>\n\n"
            f"📝 Принято заданий: {len(accepted)}\n"
            f"{pending_text}\n"
            f"✅ Одобрено отчётов: {approved_count}\n"
            f"❌ Отклонено отчётов: {rejected_count}\n\n"
            f"🏅 Баллы за всё время: {total_points}\n"
            f"📆 Баллы за неделю: {weekly_points} (сброс в 00:01 по Мск)\n"
        ),
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "❓ Помощь")
async def show_help(message: Message):
    """Показать FAQ."""
    help_text = (
        "❓ <b>FAQ — Часто задаваемые вопросы:</b>\n\n"
        "<b>1. Как участвовать в челленджах?</b>\n"
        "Выбери задание из списка, выполни его и отправь фото-отчёт.\n\n"
        "<b>2. Что дают баллы?</b>\n"
        "Баллы повышают твоё место в рейтинге участников. Чем больше заданий ты выполняешь, тем выше твой уровень 🌟\n\n"
        "<b>3. Нужно ли что-то платить?</b>\n"
        "Нет, участие полностью бесплатное 💚\n\n"
        "<b>4. Не вижу новых заданий.</b>\n"
        "Если все текущие челленджи выполнены, дождись обновления — мы пришлём новые!"
    )
    await message.answer_photo(
        photo=FSInputFile("images/help_banner.jpg"),
        caption=help_text,
        reply_markup=get_main_menu(),
    )

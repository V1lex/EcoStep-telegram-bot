from datetime import datetime, timedelta
from html import escape
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, Message

from config.admins import has_admin_panel, is_admin
from config.challenges import get_all_challenges, get_challenge
from database import (
    accept_challenge,
    add_friend,
    create_friend_request,
    decline_challenge,
    find_user_by_username,
    get_accepted_challenges,
    get_friend_ids,
    get_friend_request,
    get_friends,
    get_reviewed_challenges,
    get_submitted_challenges,
    get_user_challenge_statuses,
    get_user_awarded_stats,
    get_user_review_summary,
    get_users_by_ids,
    mark_challenge_submitted,
    remove_friend,
    update_friend_request_status,
)
from keyboards.all_keyboards import (
    get_back_button,
    get_challenge_actions_keyboard,
    get_friend_actions_keyboard,
    get_friend_cancel_keyboard,
    get_friend_confirmation_keyboard,
    get_friend_remove_keyboard,
    get_friend_request_keyboard,
    get_main_menu,
    get_report_challenges_keyboard,
    get_report_confirmation_keyboard,
    get_tasks_keyboard,
)
from utils.admin_panel import send_admin_panel_prompt
import re

def _parse_co2_value(co2_text: str) -> float | None:
    """Извлекает первое число из строки вроде '~1.1 кг CO₂' → 1.1"""
    if not co2_text:
        return None
    match = re.search(r"[\d.]+", co2_text)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None

router = Router()

# Временное хранилище выбранных заданий для отчёта
pending_reports: dict[int, str] = {}
# Временное хранилище данных отправленного файла до подтверждения
pending_report_payloads: dict[int, tuple[str, str | None, str, str | None]] = {}
# Временное состояние диалогов в разделе друзей
friend_states: dict[int, dict[str, Any]] = {}


def _get_week_start_msk() -> datetime:
    now_msk = datetime.utcnow() + timedelta(hours=3)
    start_date = now_msk.date() - timedelta(days=now_msk.weekday())
    start_dt = datetime.combine(start_date, datetime.min.time()) + timedelta(minutes=1)
    if now_msk < start_dt:
        start_dt -= timedelta(days=7)
    return start_dt


def _resolve_points_value(
    challenge_id: str,
    stored_points: int | None,
    challenges_cache: dict[str, dict],
) -> int:
    if stored_points is not None:
        try:
            return int(stored_points)
        except (TypeError, ValueError):
            return 0
    details = challenges_cache.get(challenge_id) or get_challenge(challenge_id)
    if not details:
        return 0
    value = details.get("points_value")
    if isinstance(value, int):
        return value
    points_field = details.get("points")
    if isinstance(points_field, int):
        return points_field
    if isinstance(points_field, str):
        digits = "".join(ch for ch in points_field if ch.isdigit())
        if digits:
            try:
                return int(digits)
            except ValueError:
                return 0
    return 0


def _calculate_user_stats(user_id: int, challenges_cache: dict[str, dict]) -> tuple[int, int, float]:
    awarded = get_user_awarded_stats(user_id)
    week_start = _get_week_start_msk()
    total_points = 0
    weekly_points = 0
    total_co2 = 0.0

    for challenge_id, points_value, reviewed_at in awarded:
        # Баллы
        points = _resolve_points_value(challenge_id, points_value, challenges_cache)
        total_points += points

        # CO₂
        challenge = challenges_cache.get(challenge_id) or get_challenge(challenge_id)
        co2_text = challenge.get("co2", "") if challenge else ""
        co2_value = _parse_co2_value(co2_text)
        if co2_value is not None:
            total_co2 += co2_value

        # Еженедельные баллы
        if reviewed_at:
            try:
                reviewed_dt = datetime.strptime(reviewed_at, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                reviewed_dt = None
            if reviewed_dt and reviewed_dt >= week_start:
                weekly_points += points

    return total_points, weekly_points, total_co2

def _build_display_label(record: dict[str, Any] | None, fallback_id: int) -> str:
    if not record:
        return f"ID {fallback_id}"
    first_name = (record.get("first_name") or "").strip()
    username = (record.get("username") or "").strip()
    if first_name and username:
        return f"{first_name} (@{username})"
    if first_name:
        return first_name
    if username:
        return f"@{username}"
    return f"ID {fallback_id}"


def _render_leaderboard_section(
    entries: list[dict[str, Any]],
    user_id: int,
    field: str,
    title: str,
) -> str:
    if not entries:
        return f"{title}\n—"

    def _sort_key(item: dict[str, Any]):
        return (-int(item[field]), -int(item.get("total", 0)), item["label"].lower())

    sorted_entries = sorted(entries, key=_sort_key)
    lines: list[str] = []
    for index, entry in enumerate(sorted_entries, start=1):
        marker = " <i>(это ты)</i>" if entry["user_id"] == user_id else ""
        lines.append(
            f"{index}. {escape(entry['label'])} — {int(entry[field])}{marker}"
        )
    return f"{title}\n" + "\n".join(lines)


def _build_friends_panel(user_id: int) -> tuple[str, bool]:
    friends = get_friends(user_id)
    participants = [user_id] + [friend["user_id"] for friend in friends]
    challenges_cache = get_all_challenges()
    users_map = get_users_by_ids(participants)
    entries: list[dict[str, Any]] = []
    for participant_id in participants:
        total_points, weekly_points, total_co2 = _calculate_user_stats(participant_id, challenges_cache)
        label = _build_display_label(users_map.get(participant_id), participant_id)
        entries.append(
            {
                "user_id": participant_id,
                "label": label,
                "weekly": weekly_points,
                "total": total_points,
                "co2": total_co2,
            }
        )

    weekly_block = _render_leaderboard_section(entries, user_id, "weekly", "📆 <b>Баллы за неделю</b>")
    total_block = _render_leaderboard_section(entries, user_id, "total", "🏆 <b>Баллы за всё время</b>")
    hint = (
        "\n\nДобавьте друзей, чтобы сравнивать прогресс!"
        if not friends
        else ""
    )
    content = (
        "🏅 <b>Рейтинг между друзьями</b>\n"
        f"Друзей: {len(friends)}\n\n"
        f"{weekly_block}\n\n{total_block}{hint}"
    )
    return content, bool(friends)


def _friends_panel_payload(user_id: int):
    text, has_friends = _build_friends_panel(user_id)
    keyboard = get_friend_actions_keyboard(has_friends)
    return text, keyboard


def _get_user_label(user_id: int) -> str:
    """Получить отображаемое имя пользователя."""
    record = get_users_by_ids([user_id]).get(user_id)
    return _build_display_label(record, user_id)


async def _send_friend_request_prompt(bot, target_id: int, requester_label: str, request_id: int):
    """Отправить уведомление о новой заявке в друзья."""
    text = (
        f"🤝 <b>{escape(requester_label)}</b> хочет добавить вас в друзья.\n"
        "Примите или отклоните запрос ниже."
    )
    try:
        await bot.send_message(
            target_id,
            text,
            reply_markup=get_friend_request_keyboard(request_id),
        )
    except Exception:
        pass


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
        reply_markup=get_main_menu(),
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
    submitted = mark_challenge_submitted(
        user_id,
        challenge_id,
        file_id,
        caption,
        attachment_type,
        attachment_name,
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
    pending_submissions = get_submitted_challenges(user_id, only_pending=True)
    summary = get_user_review_summary(user_id)
    approved_count = summary.get('approved', 0)
    rejected_count = summary.get('rejected', 0)
    pending_count = summary.get('pending', len(pending_submissions))

    challenges = get_all_challenges()
    total_points, weekly_points, total_co2 = _calculate_user_stats(user_id, challenges)

    if pending_submissions:
        pending_lines = "\n".join(
            f"• {challenges.get(challenge_id, {}).get('title', challenge_id)}"
            for challenge_id, *_ in pending_submissions
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
            f"🌱 Сэкономлено CO₂: {total_co2:.1f} кг\n"
        ),
        reply_markup=get_main_menu(),
    )


@router.message(F.text == "🏅 Рейтинг друзей")
async def show_friends(message: Message):
    """Показать рейтинг среди друзей."""
    user_id = message.from_user.id
    text, keyboard = _friends_panel_payload(user_id)
    await message.answer(text, reply_markup=keyboard)


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


@router.callback_query(F.data == "friends:refresh")
async def refresh_friends(callback: CallbackQuery):
    """Обновить показатели рейтинга."""
    user_id = callback.from_user.id
    text, keyboard = _friends_panel_payload(user_id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer("Рейтинг обновлён")


@router.callback_query(F.data == "friends:add")
async def prompt_friend_username(callback: CallbackQuery):
    """Запросить username друга."""
    user_id = callback.from_user.id
    friend_states[user_id] = {"stage": "await_username"}
    await callback.message.answer(
        "Введите username друга (без @). Отправьте «отмена», чтобы прервать.",
        reply_markup=get_friend_cancel_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "friends:remove")
async def prompt_friend_removal(callback: CallbackQuery):
    """Показать список друзей для удаления."""
    user_id = callback.from_user.id
    friends = get_friends(user_id)
    if not friends:
        await callback.answer("Список друзей пуст.", show_alert=True)
        return
    items = [
        (friend["user_id"], _build_display_label(friend, friend["user_id"]))
        for friend in friends
    ]
    await callback.message.answer(
        "Выберите друга, которого хотите убрать из рейтинга.",
        reply_markup=get_friend_remove_keyboard(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("friends:remove_select:"))
async def remove_friend_callback(callback: CallbackQuery):
    """Удалить выбранного друга."""
    user_id = callback.from_user.id
    try:
        friend_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный выбор.", show_alert=True)
        return
    removed = remove_friend(user_id, friend_id)
    response_text = "Друг удалён." if removed else "Этого пользователя уже нет в списке друзей."
    try:
        await callback.message.edit_text(response_text, reply_markup=None)
    except Exception:
        await callback.message.answer(response_text)
    text, keyboard = _friends_panel_payload(user_id)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("friends:confirm_add:"))
async def confirm_friend_add(callback: CallbackQuery):
    """Подтвердить добавление друга."""
    user_id = callback.from_user.id
    try:
        friend_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректный пользователь.", show_alert=True)
        return
    state = friend_states.get(user_id)
    if not state or state.get("friend_id") != friend_id:
        await callback.answer("Нет кандидата для добавления.", show_alert=True)
        return
    friend_states.pop(user_id, None)
    friend_record = state.get("friend_record") or {"user_id": friend_id}
    friend_label = _build_display_label(friend_record, friend_id)
    requester_label = _build_display_label(
        {
            "first_name": callback.from_user.first_name,
            "username": callback.from_user.username,
        },
        user_id,
    )
    result = create_friend_request(user_id, friend_id)
    status = result.get("status")

    if status == "self":
        response_text = "Нельзя добавить себя в друзья."
        alert_text = "Это вы 🙂"
    elif status == "already_friends":
        response_text = "Этот пользователь уже есть в списке друзей."
        alert_text = "Уже друзья"
    elif status == "already_pending":
        response_text = "Заявка уже отправлена. Ждите подтверждения."
        alert_text = "Ждём подтверждения"
    elif status == "auto_accepted":
        response_text = f"{escape(friend_label)} уже оставил заявку — дружба подтверждена."
        alert_text = "Заявка совпала"
        try:
            await callback.bot.send_message(
                friend_id,
                f"👍 <b>{escape(requester_label)}</b> принял(а) вашу заявку. Вы теперь друзья.",
            )
        except Exception:
            pass
    elif status == "created":
        response_text = "Заявка отправлена. Мы сообщим, когда друг подтвердит."
        alert_text = "Заявка отправлена"
        request_id = result.get("request_id")
        if request_id:
            await _send_friend_request_prompt(callback.bot, friend_id, requester_label, request_id)
    else:
        response_text = "Не удалось отправить заявку. Попробуйте позже."
        alert_text = "Ошибка"

    try:
        await callback.message.edit_text(response_text, reply_markup=None)
    except Exception:
        await callback.message.answer(response_text)
    text, keyboard = _friends_panel_payload(user_id)
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer(alert_text)


@router.callback_query(F.data == "friends:cancel")
async def cancel_friend_flow(callback: CallbackQuery):
    """Отменить начатое действие с друзьями."""
    user_id = callback.from_user.id
    friend_states.pop(user_id, None)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer("Отменено")


@router.callback_query(F.data.startswith("friends:req_accept:"))
async def accept_friend_request_callback(callback: CallbackQuery):
    """Подтвердить входящую заявку в друзья."""
    user_id = callback.from_user.id
    try:
        request_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    request = get_friend_request(request_id)
    if not request:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if request["target_id"] != user_id:
        await callback.answer("Эта заявка предназначена другому пользователю.", show_alert=True)
        return
    if request["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    updated = update_friend_request_status(request_id, "accepted")
    if not updated:
        await callback.answer("Не удалось принять заявку.", show_alert=True)
        return

    add_friend(request["requester_id"], request["target_id"])
    requester_label = _get_user_label(request["requester_id"])
    target_label = _get_user_label(user_id)
    try:
        await callback.message.edit_text(
            "Заявка принята. Вы добавлены в список друзей.",
            reply_markup=None,
        )
    except Exception:
        await callback.message.answer("Заявка принята. Вы добавлены в список друзей.")
    text, keyboard = _friends_panel_payload(user_id)
    await callback.message.answer(text, reply_markup=keyboard)
    try:
        await callback.bot.send_message(
            request["requester_id"],
            f"🎉 <b>{escape(target_label)}</b> принял(а) вашу заявку в друзья.",
        )
    except Exception:
        pass
    await callback.answer("Друг добавлен")


@router.callback_query(F.data.startswith("friends:req_decline:"))
async def decline_friend_request_callback(callback: CallbackQuery):
    """Отклонить входящую заявку в друзья."""
    user_id = callback.from_user.id
    try:
        request_id = int(callback.data.split(":")[-1])
    except ValueError:
        await callback.answer("Некорректная заявка.", show_alert=True)
        return

    request = get_friend_request(request_id)
    if not request:
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    if request["target_id"] != user_id:
        await callback.answer("Эта заявка предназначена другому пользователю.", show_alert=True)
        return
    if request["status"] != "pending":
        await callback.answer("Заявка уже обработана.", show_alert=True)
        return

    updated = update_friend_request_status(request_id, "declined")
    if not updated:
        await callback.answer("Не удалось отклонить заявку.", show_alert=True)
        return

    try:
        await callback.message.edit_text("Заявка отклонена.", reply_markup=None)
    except Exception:
        await callback.message.answer("Заявка отклонена.")
    text, keyboard = _friends_panel_payload(user_id)
    await callback.message.answer(text, reply_markup=keyboard)
    target_label = _get_user_label(user_id)
    try:
        await callback.bot.send_message(
            request["requester_id"],
            f"⚠️ <b>{escape(target_label)}</b> отклонил(а) вашу заявку в друзья.",
        )
    except Exception:
        pass
    await callback.answer("Заявка отклонена")


@router.message(lambda message: friend_states.get(message.from_user.id, {}).get("stage") == "await_username")
async def collect_friend_username(message: Message):
    """Получить username друга от пользователя."""
    user_id = message.from_user.id
    entered = (message.text or "").strip()
    if not entered:
        await message.answer("Введите username друга (без @).")
        return
    if entered.lower() in {"отмена", "cancel"}:
        friend_states.pop(user_id, None)
        await message.answer("Добавление отменено.")
        return

    username = entered.lstrip("@").strip()
    if not username:
        await message.answer("Введите корректный username.")
        return

    candidate = find_user_by_username(username)
    if not candidate:
        await message.answer(
            "Пользователь с таким username не найден. Убедитесь, что друг запускал бота.",
        )
        return

    friend_id = candidate[0]
    if friend_id == user_id:
        await message.answer("Нельзя добавить себя в друзья.")
        return

    existing = {friend["user_id"] for friend in get_friends(user_id)}
    if friend_id in existing:
        await message.answer("Этот пользователь уже есть в списке друзей.")
        return

    friend_record = {
        "user_id": friend_id,
        "username": candidate[1],
        "first_name": candidate[2],
    }
    friend_states[user_id] = {
        "stage": "confirm_add",
        "friend_id": friend_id,
        "friend_record": friend_record,
    }
    label = escape(_build_display_label(friend_record, friend_id))
    await message.answer(
        f"Отправить заявку {label}? Мы попросим друга подтвердить дружбу.",
        reply_markup=get_friend_confirmation_keyboard(friend_id),
    )

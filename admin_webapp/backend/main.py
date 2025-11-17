import secrets
from html import escape
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from admin_webapp.backend.schemas import (
    AdminLogEntry,
    BroadcastRequest,
    ChallengeCreateRequest,
    ChallengeResponse,
    ChallengeUpdateRequest,
    LoginRequest,
    LoginResponse,
    ReportActionRequest,
    ReportResponse,
)
from config.admins import (
    ADMIN_CREDENTIALS,
    ADMIN_IDS,
    ADMIN_PANEL_PASSWORD,
    validate_admin_password,
)
from config.challenges import get_all_challenges, get_challenge
from create_bot import bot
from database import (
    create_custom_challenge,
    delete_custom_challenge,
    fetch_custom_challenges,
    get_admin_logs,
    get_all_user_ids,
    get_friend_ids,
    get_custom_challenge,
    get_pending_reports,
    get_user_info,
    init_db,
    log_admin_action,
    set_custom_challenge_active,
    update_report_review,
)

security = HTTPBearer(auto_error=False)
active_tokens: Dict[str, int] = {}


async def build_file_url(file_id: Optional[str]) -> Optional[str]:
    if not file_id:
        return None
    try:
        telegram_file = await bot.get_file(file_id)
    except Exception:
        return None
    return f"https://api.telegram.org/file/bot{bot.token}/{telegram_file.file_path}"


def get_app() -> FastAPI:
    """Создать и настроить FastAPI-приложение."""
    load_dotenv()
    init_db()

    app = FastAPI(title="EcoStep Admin API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_router = APIRouter(prefix="/api")

    @api_router.post("/auth/login", response_model=LoginResponse)
    async def login(data: LoginRequest):
        if not ADMIN_PANEL_PASSWORD and not ADMIN_CREDENTIALS:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Пароль для админ-панели не настроен.",
            )

        if data.admin_id not in ADMIN_IDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="ID не имеет прав администратора.",
            )

        if not validate_admin_password(data.admin_id, data.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный пароль.",
            )

        token = secrets.token_urlsafe(32)
        active_tokens[token] = data.admin_id
        log_admin_action(data.admin_id, "login", "Вход в админ-панель")
        return LoginResponse(token=token, admin_id=data.admin_id)

    @api_router.post("/auth/logout")
    async def logout(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ):
        if credentials:
            active_tokens.pop(credentials.credentials, None)
        return {"status": "ok"}

    async def current_admin(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> int:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Токен не передан.",
            )
        token = credentials.credentials
        admin_id = active_tokens.get(token)
        if not admin_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недействительный токен.",
            )
        if admin_id not in ADMIN_IDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав администратора.",
            )
        return admin_id

    @api_router.get("/challenges", response_model=list[ChallengeResponse])
    async def list_challenges(_: int = Depends(current_admin)):
        challenges = get_all_challenges()
        custom = fetch_custom_challenges(active_only=False)
        response: list[ChallengeResponse] = []
        for challenge_id, data in challenges.items():
            if data.get("source") == "custom":
                continue
            response.append(
                ChallengeResponse(
                    challenge_id=challenge_id,
                    title=data["title"],
                    description=data["description"],
                    points=int(data.get("points_value", 0)),
                    co2=str(data["co2"]),
                    source="default",
                    active=True,
                )
            )
        for item in custom:
            response.append(
                ChallengeResponse(
                    challenge_id=item["challenge_id"],
                    title=item["title"],
                    description=item["description"],
                    points=int(item["points"]),
                    co2=item["co2"],
                    source="custom",
                    active=bool(item["active"]),
                )
            )
        return response

    @api_router.post("/challenges", response_model=ChallengeResponse)
    async def add_challenge(
        payload: ChallengeCreateRequest,
        admin_id: int = Depends(current_admin),
    ):
        challenge_id = create_custom_challenge(
            payload.title,
            payload.description,
            payload.points,
            payload.co2,
        )
        log_admin_action(
            admin_id,
            "create_challenge",
            f"{challenge_id}: {payload.title}",
        )
        return ChallengeResponse(
            challenge_id=challenge_id,
            title=payload.title,
            description=payload.description,
            points=payload.points,
            co2=payload.co2,
            source="custom",
            active=True,
        )

    @api_router.patch("/challenges/{challenge_id}", response_model=ChallengeResponse)
    async def update_challenge(
        challenge_id: str,
        payload: ChallengeUpdateRequest,
        admin_id: int = Depends(current_admin),
    ):
        challenge = get_custom_challenge(challenge_id)
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задание не найдено или недоступно для изменения.",
            )

        updated = set_custom_challenge_active(challenge_id, payload.active)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось обновить состояние задания.",
            )

        refreshed = get_custom_challenge(challenge_id)
        if not refreshed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Задание не найдено после обновления.",
            )

        action = "activate_challenge" if payload.active else "deactivate_challenge"
        log_admin_action(
            admin_id,
            action,
            f"{challenge_id}: {refreshed['title']}",
        )

        return ChallengeResponse(
            challenge_id=refreshed["challenge_id"],
            title=refreshed["title"],
            description=refreshed["description"],
            points=int(refreshed["points"]),
            co2=str(refreshed["co2"]),
            source="custom",
            active=bool(refreshed["active"]),
        )

    @api_router.delete("/challenges/{challenge_id}")
    async def delete_challenge_endpoint(
        challenge_id: str,
        admin_id: int = Depends(current_admin),
    ):
        challenge = get_custom_challenge(challenge_id)
        if not challenge:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Удаляемое задание не найдено.",
            )
        deleted = delete_custom_challenge(challenge_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Не удалось удалить задание.",
            )
        log_admin_action(
            admin_id,
            "delete_challenge",
            f"{challenge_id}: {challenge['title']}",
        )
        return {"status": "deleted"}

    @api_router.post("/broadcast")
    async def broadcast(
        payload: BroadcastRequest,
        admin_id: int = Depends(current_admin),
    ):
        user_ids = get_all_user_ids()
        sent = 0
        failed = 0
        for user_id in user_ids:
            try:
                await bot.send_message(user_id, payload.message)
                sent += 1
            except Exception:
                failed += 1
        log_admin_action(
            admin_id,
            "broadcast",
            f"sent={sent}, failed={failed}",
        )
        return {"sent": sent, "failed": failed, "total": len(user_ids)}

    @api_router.get("/reports/pending", response_model=list[ReportResponse])
    async def pending_reports(_: int = Depends(current_admin)):
        reports = get_pending_reports()
        responses: list[ReportResponse] = []
        challenges_cache = get_all_challenges()
        for report in reports:
            details = challenges_cache.get(report["challenge_id"]) or get_challenge(report["challenge_id"])
            title = details["title"] if details else report["challenge_id"]
            file_url = await build_file_url(report["photo_file_id"])
            responses.append(
                ReportResponse(
                    user_id=report["user_id"],
                    username=report["username"],
                    first_name=report["first_name"],
                    challenge_id=report["challenge_id"],
                    challenge_title=title,
                    submitted_at=report["submitted_at"],
                    caption=report["caption"],
                    attachment_type=report["attachment_type"],
                    attachment_name=report["attachment_name"],
                    file_id=report["photo_file_id"],
                    file_url=file_url,
                )
            )
        return responses

async def _notify_user(
    user_id: int,
    message: str,
):
    try:
        await bot.send_message(user_id, message)
    except Exception:
        pass


def _format_user_display(user_id: int) -> str:
    info = get_user_info(user_id)
    if not info:
        return f"ID {user_id}"
    _, username, first_name, *_ = info
    first_name = (first_name or "").strip()
    username = (username or "").strip()
    if first_name and username:
        return f"{first_name} (@{username})"
    if first_name:
        return first_name
    if username:
        return f"@{username}"
    return f"ID {user_id}"


async def _notify_friends_about_completion(user_id: int, challenge_title: str, points: int | None):
    friend_ids = get_friend_ids(user_id)
    if not friend_ids:
        return
    friend_message = (
        f"🎉 Ваш друг <b>{escape(_format_user_display(user_id))}</b> выполнил задание "
        f"<b>{escape(challenge_title)}</b>."
    )
    if points:
        friend_message += f"\n🏅 Он заработал {points} баллов."
    for friend_id in friend_ids:
        if friend_id == user_id:
            continue
        await _notify_user(friend_id, friend_message)

    def _get_challenge_points_value(challenge_id: str) -> int:
        details = get_challenge(challenge_id)
        if details and isinstance(details.get("points_value"), int):
            return int(details["points_value"])
        if details and isinstance(details.get("points"), int):
            return int(details["points"])
        for item in fetch_custom_challenges(active_only=False):
            if item["challenge_id"] == challenge_id:
                try:
                    return int(item["points"])
                except (TypeError, ValueError):
                    return 0
        return 0

    @api_router.post("/reports/resolve")
    async def resolve_report(
        payload: ReportActionRequest,
        admin_id: int = Depends(current_admin),
    ):
        decision = payload.decision
        points_value = _get_challenge_points_value(payload.challenge_id) if decision == "approved" else None
        updated = update_report_review(
            payload.user_id,
            payload.challenge_id,
            decision,
            payload.comment,
            points_value,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Отчёт не найден или уже обработан.",
            )
        challenge = get_challenge(payload.challenge_id)
        challenge_title = challenge["title"] if challenge else payload.challenge_id
        decision_text = "одобрен" if decision == "approved" else "отклонён"
        log_admin_action(
            admin_id,
            "resolve_report",
            f"{payload.user_id}:{payload.challenge_id}:{decision}",
        )
        user_message = (
            f"📄 Отчёт по заданию <b>{challenge_title}</b> {decision_text}."
        )
        if decision == "approved" and points_value:
            user_message += f"\n🏅 Начислено баллов: {points_value}"
        if payload.comment:
            user_message += f"\n💬 Комментарий модератора: {payload.comment}"
        if decision == "rejected":
            user_message += "\n🔁 Задание снова доступно для принятия."
        await _notify_user(payload.user_id, user_message)
        if decision == "approved":
            await _notify_friends_about_completion(
                payload.user_id,
                challenge_title,
                points_value,
            )
        return {"status": "ok"}

    @api_router.get("/logs", response_model=list[AdminLogEntry])
    async def admin_logs(_: int = Depends(current_admin)):
        logs = get_admin_logs(limit=None)
        return [
            AdminLogEntry(
                id=entry["id"],
                admin_id=entry["admin_id"],
                action=entry["action"],
                details=entry["details"],
                created_at=entry["created_at"],
            )
            for entry in logs
        ]

    app.include_router(api_router)

    static_dir = Path(__file__).resolve().parent.parent
    app.mount(
        "/",
        StaticFiles(directory=str(static_dir), html=True),
        name="static",
    )
    return app


app = get_app()

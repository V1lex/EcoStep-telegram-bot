from database import fetch_custom_challenges, get_custom_challenge

Challenge = dict[str, str | int | bool]


DEFAULT_CHALLENGES: dict[str, Challenge] = {
    "task_1": {
        "title": "🚰 Отказаться от одноразовой бутылки",
        "description": "Вместо покупки пластиковой бутылки используй свою многоразовую в течение дня.",
        "points": "5 баллов",
        "points_value": 5,
        "co2": "0.1 кг CO₂",
    },
    "task_2": {
        "title": "🚶 Пойти пешком до учёбы",
        "description": "Если расстояние до учёбы меньше 2 км, пройди его пешком вместо транспорта.",
        "points": "10 баллов",
        "points_value": 10,
        "co2": "0.5 кг CO₂",
    },
    "task_3": {
        "title": "📄 Сдать макулатуру",
        "description": "Собери и сдай макулатуру (минимум 1 кг) в пункт приёма вторсырья.",
        "points": "15 баллов",
        "points_value": 15,
        "co2": "1.2 кг CO₂",
    },
    "task_4": {
        "title": "♻️ Использовать многоразовую сумку",
        "description": "Вместо пластикового пакета в магазине используй свою многоразовую сумку.",
        "points": "5 баллов",
        "points_value": 5,
        "co2": "0.08 кг CO₂",
    },
    "task_5": {
        "title": "💡 Выключить свет на час",
        "description": "В течение часа используй естественное освещение или работай при свечах.",
        "points": "7 баллов",
        "points_value": 7,
        "co2": "0.3 кг CO₂",
    },
}


def get_challenge(challenge_id: str) -> Challenge | None:
    """Получить описание челленджа по его идентификатору."""
    if challenge_id in DEFAULT_CHALLENGES:
        return DEFAULT_CHALLENGES[challenge_id]

    challenge = get_custom_challenge(challenge_id)
    if not challenge or not challenge.get("active", True):
        return None

    points_value = challenge["points"]
    return {
        "title": challenge["title"],
        "description": challenge["description"],
        "points": f"{points_value} баллов",
        "points_value": points_value,
        "co2": challenge["co2"],
        "source": "custom",
        "challenge_id": challenge_id,
    }


def get_all_challenges() -> dict[str, Challenge]:
    """Вернуть полный список челленджей."""
    challenges = {
        challenge_id: data.copy()
        for challenge_id, data in DEFAULT_CHALLENGES.items()
    }
    for custom in fetch_custom_challenges(active_only=True):
        challenge_id = custom["challenge_id"]
        points_value = custom["points"]
        challenges[challenge_id] = {
            "title": custom["title"],
            "description": custom["description"],
            "points": f"{points_value} баллов",
            "points_value": points_value,
            "co2": custom["co2"],
            "source": "custom",
            "challenge_id": challenge_id,
        }
    return challenges

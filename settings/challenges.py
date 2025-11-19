from database import fetch_custom_challenges, get_custom_challenge

Challenge = dict[str, str | int | bool]


DEFAULT_CHALLENGES: dict[str, Challenge] = {}


def get_challenge(challenge_id: str) -> Challenge | None:
    """Получить описание челленджа по его идентификатору."""
    if challenge_id in DEFAULT_CHALLENGES:
        challenge = DEFAULT_CHALLENGES[challenge_id].copy()
        challenge.setdefault("co2_quantity_based", False)
        return challenge

    challenge = get_custom_challenge(challenge_id)
    if not challenge or not challenge.get("active", True):
        return None

    points_value = challenge["points"]
    quantity_based = bool(challenge.get("co2_quantity_based", False))
    return {
        "title": challenge["title"],
        "description": challenge["description"],
        "points": f"{points_value} баллов",
        "points_value": points_value,
        "co2": challenge["co2"],
        "source": "custom",
        "challenge_id": challenge_id,
        "co2_quantity_based": quantity_based,
    }


def get_all_challenges() -> dict[str, Challenge]:
    """Вернуть полный список челленджей."""
    challenges: dict[str, Challenge] = {}
    for challenge_id, data in DEFAULT_CHALLENGES.items():
        copy = data.copy()
        copy.setdefault("co2_quantity_based", False)
        challenges[challenge_id] = copy
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
            "co2_quantity_based": bool(custom.get("co2_quantity_based", False)),
        }
    return challenges

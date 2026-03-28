from datetime import datetime, timezone

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

def format_s3_key(entity: str, file_format: str = "json") -> str:
    now = get_utc_now()
    return (
        f"raw/{entity}/"
        f"year={now.year}/"
        f"month={now.month:02d}/"
        f"day={now.day:02d}/"
        f"{entity}_{now.strftime('%Y%m%d_%H%M%S')}.{file_format}"
    )

def get_run_date() -> str:
    return get_utc_now().strftime("%Y-%m-%d")


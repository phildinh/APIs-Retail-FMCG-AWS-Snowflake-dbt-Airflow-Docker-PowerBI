from datetime import datetime, timezone
from typing import List, Dict, Any

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

def enrich_records(
        entity: str,
        data:   List[Dict],
        run_id: str,
) -> List[Dict]:
    loaded_at = get_utc_now().isoformat()
    load_date = get_run_date()

    for record in data:
        record["_loaded_at"] =  loaded_at
        record["_source"] =     "fakestoreapi"
        record["_entity"] =     entity
        record["_load_date"] =  load_date
        record["_run_id"] =     run_id

    return data
from ingestion.storage.db import get_snowflake_connection
from ingestion.core.logger import get_logger

logger = get_logger(__name__)


def build_copy_query(entity: str, s3_key: str) -> str:
    table_map = {
        "products": {
            "table": "RAW.PRODUCTS",
            "columns": """
                id, title, price, description, category, image,
                rating, _loaded_at, _source, _entity, _load_date, _run_id
            """,
            "select": """
                $1:id::NUMBER,
                $1:title::VARCHAR,
                $1:price::FLOAT,
                $1:description::VARCHAR,
                $1:category::VARCHAR,
                $1:image::VARCHAR,
                $1:rating::VARIANT,
                $1:_loaded_at::TIMESTAMP_TZ,
                $1:_source::VARCHAR,
                $1:_entity::VARCHAR,
                $1:_load_date::DATE,
                $1:_run_id::VARCHAR
            """
        },
        "users": {
            "table": "RAW.USERS",
            "columns": """
                id, email, username, password, name,
                address, phone, _loaded_at, _source, _entity, _load_date, _run_id
            """,
            "select": """
                $1:id::NUMBER,
                $1:email::VARCHAR,
                $1:username::VARCHAR,
                $1:password::VARCHAR,
                $1:name::VARIANT,
                $1:address::VARIANT,
                $1:phone::VARCHAR,
                $1:_loaded_at::TIMESTAMP_TZ,
                $1:_source::VARCHAR,
                $1:_entity::VARCHAR,
                $1:_load_date::DATE,
                $1:_run_id::VARCHAR
            """
        },
        "carts": {
            "table": "RAW.CARTS",
            "columns": """
                id, userid, date, products,
                _loaded_at, _source, _entity, _load_date, _run_id
            """,
            "select": """
                $1:id::NUMBER,
                $1:userId::NUMBER,
                $1:date::TIMESTAMP_TZ,
                $1:products::VARIANT,
                $1:_loaded_at::TIMESTAMP_TZ,
                $1:_source::VARCHAR,
                $1:_entity::VARCHAR,
                $1:_load_date::DATE,
                $1:_run_id::VARCHAR
            """
        }
    }

    config = table_map[entity]
    entity_prefix = f"raw/{entity}/"
    sub_path = s3_key.replace(entity_prefix, "")

    logger.debug(f"entity: {entity} | sub_path: {sub_path}")

    return f"""
        COPY INTO {config['table']} (
            {config['columns']}
        )
        FROM (
            SELECT
                {config['select']}
            FROM @raw_s3_stage/{entity}/{sub_path}
        )
        FILE_FORMAT = (FORMAT_NAME = raw_json_format)
        ON_ERROR = 'CONTINUE'
    """


def copy_raw_to_snowflake(s3_keys: dict, run_id: str = None) -> dict:
    logger.info("Starting COPY INTO Snowflake RAW schema")

    conn = get_snowflake_connection()
    results = {}

    try:
        cursor = conn.cursor()

        for entity, s3_key in s3_keys.items():
            logger.info(f"Loading {entity} from {s3_key}")

            query = build_copy_query(entity, s3_key)
            cursor.execute(query)
            rows = cursor.fetchall()

            logger.debug(f"{entity} raw result: {rows}")

            rows_loaded = 0
            for row in rows:
                try:
                    rows_loaded += int(row[2]) if row[2] else 0
                except (IndexError, TypeError, ValueError):
                    pass

            results[entity] = rows_loaded
            logger.info(f"{entity}: {rows_loaded} rows loaded")

        logger.info("COPY INTO complete — summary:")
        for entity, count in results.items():
            logger.info(f"  {entity}: {count} rows")

    finally:
        conn.close()
        logger.info("Snowflake connection closed")

    return results
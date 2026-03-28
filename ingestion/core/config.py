from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):

    # Snowflake
    snowflake_account:      str
    snowflake_user:         str
    snowflake_password:     str
    snowflake_warehouse:    str
    snowflake_database:     str
    snowflake_role:         str
    snowflake_schema:       str

    # AWS
    aws_access_key_id:      str
    aws_secret_access_key:  str
    aws_region:             str
    aws_bucket_name:        str

    # FakeStoreAPI
    fakestore_base_url:     str

    # Pipeline
    environment:            str
    log_level:              str

    model_config = SettingsConfigDict(
        env_file = ".env",
        env_file_encoding = "utf_8"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
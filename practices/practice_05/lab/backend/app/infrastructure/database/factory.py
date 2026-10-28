from app.config import app_config
from app.infrastructure.database.session import SessionController

database_factory = SessionController(
    postgres_user=app_config.postgres_user,
    postgres_password=app_config.postgres_password,
    postgres_host=app_config.postgres_host,
    postgres_port=app_config.postgres_port,
    postgres_db=app_config.postgres_db,
)

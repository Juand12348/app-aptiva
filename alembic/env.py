from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.infrastructure.config import get_settings
from app.infrastructure.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
# La URL sale de .env (Settings); nunca de alembic.ini.
database_url = get_settings().database_url


def include_object(object_, name, type_, reflected, compare_to) -> bool:  # noqa: ANN001
    # El esquema de Neon ya existe: una tabla real sin modelo ORM nunca debe proponerse para borrar.
    if type_ == "table" and reflected and compare_to is None:
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

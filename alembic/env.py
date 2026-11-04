"""
Configuración de Alembic para el proyecto SGSM
"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy.pool import StaticPool
from alembic import context
import os
import sys

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import Base
from models import Usuario, Paciente, Medico, Especialidad, Cita, Consultorio

# Configurar logging
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Configurar metadata para migraciones automáticas
target_metadata = Base.metadata

# Obtener URL de base de datos
sqlalchemy_url = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///sgsm.db')
config.set_main_option('sqlalchemy.url', sqlalchemy_url)


def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo offline"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Ejecutar migraciones en modo online"""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = sqlalchemy_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=StaticPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

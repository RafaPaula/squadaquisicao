from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Importar todos os modelos aqui para que o Alembic autogenerate os encontre.
from app.models import candidate, job, application, resume, sync_log  # noqa: E402,F401

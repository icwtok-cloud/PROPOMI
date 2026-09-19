"""Baseline del schema productivo actual (create_all + ensure_schema_columns).

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-15

NO-OP: tablas/columnas ya existen en producción. Tras deploy:
    alembic stamp head
Migraciones futuras (0002+) deben ser incrementales. ensure_schema_columns
convive como red de seguridad hasta completar la transición.
"""
from typing import Sequence, Union

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""Garantiza en la BD que cada pregunta tenga como máximo una opción correcta.

Los triggers que mencionaba el script original no existen; este índice único parcial los reemplaza.

Revision ID: 0003_one_correct_option
Revises: 0002_student_password
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_one_correct_option"
down_revision = "0002_student_password"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_una_correcta_por_pregunta",
        "opciones_respuesta",
        ["id_pregunta"],
        unique=True,
        postgresql_where=sa.text("es_correcta"),
    )


def downgrade() -> None:
    op.drop_index("uq_una_correcta_por_pregunta", table_name="opciones_respuesta")

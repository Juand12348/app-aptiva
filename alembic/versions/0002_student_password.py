"""Agrega la contraseña del estudiante y hace obligatorio el correo (necesarios para el login).

Revision ID: 0002_student_password
Revises: 0001_baseline
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_student_password"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOT NULL directo es seguro solo porque `estudiantes` estaba vacía (verificado el 2026-11-05).
    op.add_column("estudiantes", sa.Column("contrasena_hash", sa.String(255), nullable=False))
    op.alter_column("estudiantes", "correo", existing_type=sa.String(150), nullable=False)


def downgrade() -> None:
    op.alter_column("estudiantes", "correo", existing_type=sa.String(150), nullable=True)
    op.drop_column("estudiantes", "contrasena_hash")

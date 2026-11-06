"""Modelos ORM de las tablas existentes en Neon. Nombres idénticos a la BD (fuente de verdad).

Las restricciones CHECK viven en la BD y no se repiten aquí: Alembic no las compara.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


def identity_pk() -> Mapped[int]:
    return mapped_column(Integer, Identity(always=True), primary_key=True)


class Materia(Base):
    __tablename__ = "materias"

    id_materia: Mapped[int] = identity_pk()
    nombre: Mapped[str] = mapped_column(String(100), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)


class Componente(Base):
    __tablename__ = "componentes"
    __table_args__ = (
        UniqueConstraint("id_materia", "nombre", name="uq_componente_materia"),
        UniqueConstraint("id_componente", "id_materia", name="uq_componente_id_materia"),
    )

    id_componente: Mapped[int] = identity_pk()
    id_materia: Mapped[int] = mapped_column(
        ForeignKey("materias.id_materia", name="fk_componentes_materias", ondelete="RESTRICT")
    )
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(Text)


class NivelDificultad(Base):
    __tablename__ = "niveles_dificultad"

    id_nivel: Mapped[int] = identity_pk()
    nombre: Mapped[str] = mapped_column(String(30), unique=True)
    descripcion: Mapped[str | None] = mapped_column(Text)


class Pregunta(Base):
    __tablename__ = "preguntas"
    __table_args__ = (UniqueConstraint("id_pregunta", "id_componente", name="uq_pregunta_componente"),)

    id_pregunta: Mapped[int] = identity_pk()
    id_componente: Mapped[int] = mapped_column(
        ForeignKey("componentes.id_componente", name="fk_preguntas_componentes", ondelete="RESTRICT")
    )
    id_nivel: Mapped[int] = mapped_column(
        ForeignKey("niveles_dificultad.id_nivel", name="fk_preguntas_niveles", ondelete="RESTRICT")
    )
    enunciado: Mapped[str] = mapped_column(Text)
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class OpcionRespuesta(Base):
    __tablename__ = "opciones_respuesta"
    __table_args__ = (
        UniqueConstraint("id_opcion", "id_pregunta", name="uq_opcion_pregunta"),
        UniqueConstraint("id_pregunta", "texto_opcion", name="uq_texto_opcion_pregunta"),
        # Migración 0003: como máximo una opción correcta por pregunta.
        Index(
            "uq_una_correcta_por_pregunta", "id_pregunta", unique=True, postgresql_where=text("es_correcta")
        ),
    )

    id_opcion: Mapped[int] = identity_pk()
    id_pregunta: Mapped[int] = mapped_column(
        ForeignKey("preguntas.id_pregunta", name="fk_opciones_preguntas", ondelete="CASCADE")
    )
    texto_opcion: Mapped[str] = mapped_column(Text)
    es_correcta: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class Estudiante(Base):
    __tablename__ = "estudiantes"

    id_estudiante: Mapped[int] = identity_pk()
    nombre: Mapped[str] = mapped_column(String(150))
    correo: Mapped[str] = mapped_column(String(150), unique=True)  # NOT NULL desde la migración 0002
    contrasena_hash: Mapped[str] = mapped_column(String(255))  # agregada en la migración 0002


class IntentoExamen(Base):
    __tablename__ = "intentos_examen"

    id_intento: Mapped[int] = identity_pk()
    id_estudiante: Mapped[int] = mapped_column(
        ForeignKey("estudiantes.id_estudiante", name="fk_intentos_estudiantes", ondelete="RESTRICT")
    )
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    puntaje_total: Mapped[int | None] = mapped_column(SmallInteger)
    estado: Mapped[str] = mapped_column(String(20), server_default=text("'En progreso'"))


class DetalleIntento(Base):
    __tablename__ = "detalle_intento"
    __table_args__ = (
        ForeignKeyConstraint(
            ["id_pregunta", "id_componente"],
            ["preguntas.id_pregunta", "preguntas.id_componente"],
            name="fk_detalle_pregunta_componente",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["id_opcion_seleccionada", "id_pregunta"],
            ["opciones_respuesta.id_opcion", "opciones_respuesta.id_pregunta"],
            name="fk_detalle_opcion_pregunta",
            ondelete="RESTRICT",
        ),
        UniqueConstraint("id_intento", "id_pregunta", name="uq_pregunta_por_intento"),
        UniqueConstraint("id_intento", "orden", name="uq_orden_por_intento"),
    )

    id_detalle: Mapped[int] = identity_pk()
    id_intento: Mapped[int] = mapped_column(
        ForeignKey("intentos_examen.id_intento", name="fk_detalle_intento", ondelete="CASCADE")
    )
    id_pregunta: Mapped[int] = mapped_column(Integer)
    id_componente: Mapped[int] = mapped_column(Integer)
    id_opcion_seleccionada: Mapped[int | None] = mapped_column(Integer)
    orden: Mapped[int] = mapped_column(SmallInteger)
    es_correcta: Mapped[bool | None] = mapped_column(Boolean)


class DiagnosticoIA(Base):
    __tablename__ = "diagnosticos_ia"

    id_diagnostico: Mapped[int] = identity_pk()
    id_intento: Mapped[int] = mapped_column(
        ForeignKey("intentos_examen.id_intento", name="fk_diagnosticos_intentos", ondelete="CASCADE"), unique=True
    )
    fortalezas: Mapped[str | None] = mapped_column(Text)
    debilidades: Mapped[str | None] = mapped_column(Text)
    recomendaciones: Mapped[str | None] = mapped_column(Text)
    fecha_generacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

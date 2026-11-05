# Aptiva AI — Backend

API de evaluación diagnóstica de matemáticas (FastAPI + PostgreSQL en Neon + Gemini).
Arquitectura y alcance: [PROJECT_PLAN.md](PROJECT_PLAN.md). Reglas de desarrollo: [CLAUDE.md](CLAUDE.md).

## Requisitos

- Python 3.12
- Acceso a la base de datos de Neon del proyecto

## Instalación (una sola vez)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # luego pegar el DATABASE_URL real de Neon en .env
```

`.env` nunca se sube al repositorio (está en `.gitignore`).

## Iniciar el servidor

```powershell
.venv\Scripts\activate
uvicorn app.main:app --reload
# o bien: python -m app.main
```

- API: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs
- Estado: http://127.0.0.1:8000/health → `{"status": "ok", "database": "ok"}` (503 si Neon no responde)

## Pruebas

```powershell
python -m pytest
```

Las pruebas no se conectan a Neon.

## Migraciones (Alembic)

La URL se toma de `DATABASE_URL` en `.env`. El esquema ya existe en Neon; ver §5.4 de PROJECT_PLAN.md antes de crear migraciones.

```powershell
alembic current                                   # verifica la conexión y la versión actual
alembic revision --autogenerate -m "descripcion"  # revisar el archivo generado antes de aplicarlo
alembic upgrade head
```

## Estructura

```
app/
├── domain/          # entidades y reglas (Python puro)
├── application/     # casos de uso
├── infrastructure/  # config, base de datos, modelos ORM
└── presentation/    # FastAPI: routers, schemas, dependencias
alembic/             # migraciones
tests/
```

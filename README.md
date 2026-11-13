# Aptiva AI — Backend

API de evaluación diagnóstica de matemáticas. El estudiante presenta un examen de 30 preguntas
(10 de Estadística, 10 de Geometría y 10 de Cálculo y Álgebra), el backend lo califica y Google Gemini
genera un diagnóstico con fortalezas, debilidades y recomendaciones.

Stack: Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic v2 · Alembic · PostgreSQL (Neon) · Google Gemini.
Arquitectura y alcance: [PROJECT_PLAN.md](PROJECT_PLAN.md). Reglas de desarrollo: [CLAUDE.md](CLAUDE.md).

## Instalación (una sola vez)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Completar `.env` (nunca se sube al repositorio):

| Variable | Obligatoria | Descripción |
|---|---|---|
| `DATABASE_URL` | Sí | Cadena de conexión de Neon |
| `JWT_SECRET_KEY` | Sí | Mínimo 32 caracteres. Generar con `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"` |
| `GEMINI_API_KEY` | Sí | Clave de https://aistudio.google.com/apikey |
| `CORS_ORIGINS` | No | Orígenes permitidos (JSON). Por defecto `["http://localhost:8501"]` (Streamlit) |
| `GEMINI_MODEL` | No | Por defecto `gemini-3.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | No | Por defecto 20 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Por defecto 60 |

Si falta una variable obligatoria, la app no arranca y muestra cuál falta.

## Iniciar el servidor

```powershell
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Al arrancar debe aparecer `INFO:app:Conectado a la base de datos`.

- Swagger: http://127.0.0.1:8000/docs (botón **Authorize**: correo en `username` y contraseña)
- Estado: http://127.0.0.1:8000/health

## Endpoints

| Método | Ruta | Token | Descripción |
|---|---|---|---|
| GET | `/health` | No | Estado del servidor y de la base de datos (503 si Neon no responde) |
| POST | `/api/v1/auth/register` | No | Registro (JSON: `full_name`, `email`, `password` ≥ 8) |
| POST | `/api/v1/auth/login` | No | Login (formulario: `username` = correo, `password`) → `access_token` |
| GET | `/api/v1/students/me` | Sí | Datos del estudiante |
| GET | `/api/v1/students/me/exams` | Sí | Historial de exámenes enviados |
| GET | `/api/v1/students/me/stats` | Sí | Estadísticas: evolución, componentes, dificultad y posición en el bloque |
| POST | `/api/v1/exams` | Sí | Iniciar examen (30 preguntas, sin la respuesta correcta) y `expires_at` |
| POST | `/api/v1/exams/{exam_id}/submit` | Sí | Enviar respuestas → puntajes + diagnóstico de Gemini |
| GET | `/api/v1/exams/{exam_id}/result` | Sí | Resultado y diagnóstico de un examen enviado |
| POST | `/api/v1/exams/{exam_id}/diagnosis` | Sí | Regenerar el diagnóstico (503 si Gemini no responde) |

Todos los errores tienen la forma `{"detail": "<mensaje en español>"}`:
401 sin token o con un token inválido · 404 recurso inexistente o ajeno · 409 estado inválido · 422 datos inválidos · 503 Gemini no disponible.

## Pruebas

```powershell
python -m pytest
```

Las pruebas no se conectan a Neon ni a Gemini: usan repositorios en memoria y un generador de diagnóstico falso.

## Base de datos

El esquema de Neon (9 tablas en español) es la fuente de verdad. Alembic lo registra con una migración base
(`0001_baseline`) y aplica los cambios propios del backend:

| Migración | Cambio |
|---|---|
| `0002_student_password` | `estudiantes.contrasena_hash` y `correo NOT NULL` |
| `0003_one_correct_option` | Índice único parcial: como máximo 1 opción correcta por pregunta |

```powershell
alembic current     # versión aplicada
alembic check       # confirma que los modelos coinciden con Neon
alembic upgrade head
```

Antes de aplicar una migración generada con `--autogenerate`, revisar el archivo línea por línea.

### Banco de preguntas

Ya está cargado en Neon (150 preguntas, 600 opciones). Se cargó una sola vez desde `data/*.json` con:

```powershell
python -m scripts.load_question_bank --dry-run   # solo valida
python -m scripts.load_question_bank             # valida y carga; se niega si el banco ya tiene datos
```

## Estructura

```
app/
├── domain/          # entidades, reglas de calificación (scoring.py), puertos, excepciones
├── application/     # casos de uso: auth, exams, diagnosis
├── infrastructure/  # config, BD, modelos ORM, repositorios, JWT/Argon2, cliente Gemini
└── presentation/    # FastAPI: routers, schemas, dependencias, manejo de errores
alembic/             # migraciones
scripts/             # carga única del banco de preguntas
data/                # banco de preguntas en JSON
tests/               # dominio, API y Gemini (con fakes)
```

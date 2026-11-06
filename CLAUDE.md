# CLAUDE.md — Reglas del proyecto Aptiva AI (backend)

Backend de evaluación diagnóstica de matemáticas con diagnóstico generado por Gemini.
El plan completo y el alcance están en [PROJECT_PLAN.md](PROJECT_PLAN.md). Si algo no está en el plan, no se construye sin aprobación.

## Stack (no cambiar sin aprobación)

Python 3.12 · FastAPI · SQLAlchemy 2.x (síncrono) · psycopg 3 · Pydantic v2 + pydantic-settings · Alembic · PostgreSQL en Neon · SDK `google-genai` · `pwdlib[argon2]` · `PyJWT` · `python-multipart` · pytest.

Alcance de este repositorio: **solo backend**. No crear frontend ni páginas HTML.
No agregar dependencias nuevas sin justificarlo y sin aprobación.

## Arquitectura: Clean Architecture en 4 capas

```
app/presentation → app/application → app/domain ← app/infrastructure
```

### Regla de dependencia (obligatoria)

| Capa | Puede importar | NUNCA importa |
|------|----------------|---------------|
| `domain` | Solo la biblioteca estándar | FastAPI, SQLAlchemy, Pydantic, google-genai, pwdlib, PyJWT, otras capas |
| `application` | `domain` | FastAPI, SQLAlchemy, google-genai, pwdlib, PyJWT, `infrastructure`, `presentation` |
| `infrastructure` | `domain`, librerías externas | `presentation`, `application` |
| `presentation` | `application`, `domain`, schemas Pydantic; `infrastructure` **solo** en `dependencies.py` | Modelos ORM en routers |

`dependencies.py` es el único lugar donde se conectan las implementaciones concretas con los casos de uso.

### Responsabilidades

- **Domain:** entidades (`@dataclass`), enums, funciones puras de calificación, puertos (`typing.Protocol`), excepciones de dominio. Sin E/S.
- **Application:** un caso de uso por acción del usuario (`StartExam`, `SubmitExam`, ...). Recibe puertos por constructor y expone un método `execute(...)`. Aquí se orquesta, no se calcula: los cálculos están en el dominio.
- **Infrastructure:** modelos ORM, repositorios, cliente Gemini, hash de contraseñas y JWT (`security.py`), configuración, sesión de BD. Convierte ORM ↔ entidades del dominio dentro del repositorio.
- **Presentation:** routers delgados: validan con Pydantic, llaman a un caso de uso y mapean el resultado a un schema de respuesta. Sin lógica de negocio en los routers.

## Anti-sobreingeniería

- Un puerto (`Protocol`) solo cuando hay una dependencia externa real (BD, Gemini, hash, JWT). Nada de interfaces "por si acaso".
- Nada de repositorios genéricos, *Unit of Work*, buses de eventos, CQRS, fábricas abstractas ni contenedores de inyección de dependencias.
- Un archivo por capa y módulo; dividir en paquete solo al pasar ~300 líneas.
- No agregar funcionalidades fuera del plan: roles, recuperación de contraseña, *refresh tokens*, verificación de correo, CRUD de preguntas por API, examen adaptativo, colas, caché, temporizador, frontend. Si parece necesario, preguntar primero.
- Preferir la biblioteca estándar y lo que ya existe en el código antes de escribir algo nuevo.

## Reglas de negocio no negociables

- El banco tiene 3 componentes: Estadística, Geometría, Cálculo y Álgebra; ≥50 preguntas cada uno. **Ya está cargado en Neon** (`scripts/load_question_bank.py`, carga única desde `data/*.json`): la API solo lo lee; nunca inserta, modifica ni borra preguntas.
- Cada pregunta: exactamente 4 opciones, exactamente 1 correcta. Dificultades en la BD: `Fácil`, `Medio`, `Difícil` (se leen de `niveles_dificultad`, no se fijan en el código).
- Examen: 30 preguntas = 10 aleatorias por componente, sin repetir.
- Puntaje global sobre 30; por componente sobre 10. Sin responder = incorrecta.
- Los puntajes los calcula **el backend**. Gemini solo interpreta resultados; nunca califica.
- Un examen se envía una sola vez (`'En progreso' → 'Finalizado'`); un segundo envío responde 409.

## Seguridad y privacidad

- Contraseñas solo con hash Argon2 (`pwdlib`); nunca se registran en logs ni se devuelven. Mínimo 8 caracteres.
- JWT HS256 con `sub` = id del estudiante y expiración (`ACCESS_TOKEN_EXPIRE_MINUTES`, por defecto 60). Sin *refresh tokens*.
- `JWT_SECRET_KEY` obligatorio en `Settings`; la app no arranca sin él.
- Todo endpoint salvo `/auth/*` y `/health` requiere `get_current_student`. Token ausente, inválido o vencido → 401.
- El estudiante sale **siempre del token**, nunca de la URL ni del cuerpo. Todo acceso a un examen filtra por `student_id`; un examen ajeno responde 404.
- Login fallido: mensaje genérico ("Correo o contraseña incorrectos"). Correos normalizados a minúsculas.
- **Nunca** exponer `is_correct` ni la opción correcta en respuestas de un examen en curso. Los schemas de preguntas para el estudiante son distintos de los internos.
- A Gemini solo se envían puntajes y desgloses. Nunca nombre, correo ni IDs del estudiante.
- Secretos (`DATABASE_URL`, `GEMINI_API_KEY`, `JWT_SECRET_KEY`) solo por variables de entorno vía `Settings`. `.env` nunca se versiona; mantener `.env.example` actualizado.
- Validar toda entrada externa con Pydantic en la capa de presentación. Validar que cada opción enviada pertenezca a su pregunta y al examen.
- SQL siempre a través de SQLAlchemy (sin concatenar strings).

## Base de datos

- **El esquema de Neon ya existe y es la fuente de verdad** (§5 de PROJECT_PLAN.md): `materias`, `componentes`, `niveles_dificultad`, `preguntas`, `opciones_respuesta`, `estudiantes`, `intentos_examen`, `detalle_intento`, `diagnosticos_ia`. Los modelos ORM usan esos nombres exactos de tablas y columnas, en español.
- No crear tablas nuevas. La única migración de esquema prevista es la contraseña en `estudiantes`. Cualquier otro cambio necesita aprobación.
- Una migración nunca borra ni reescribe datos existentes. El *autogenerate* se revisa línea por línea: cualquier `drop_*` o `alter_*` inesperado significa que un modelo no coincide con la BD; se corrige el modelo, no la BD.
- El backend solo lee las preguntas con `activa = TRUE`.
- Puntaje por componente: se deriva de `detalle_intento` agrupando por `id_componente`; no se guarda aparte.
- Estados de `intentos_examen`: `'En progreso'` → `'Finalizado'`. `'Cancelado'` no se usa.
- `diagnosticos_ia` guarda texto: un elemento por línea; el repositorio separa y une las listas.
- Todo cambio de esquema pasa por una migración Alembic (`alembic revision --autogenerate -m "..."`), revisada a mano antes de hacer commit. Nunca `Base.metadata.create_all()` fuera de las pruebas.
- Las invariantes se expresan también como restricciones (`CHECK`, `UNIQUE`, FK, índice único parcial), no solo en Python.
- Nombres: la BD y los modelos ORM en español (tal como existen). Dominio, casos de uso, schemas y API en inglés. La traducción ocurre solo en los repositorios.
- Neon: `sslmode=require`, `pool_pre_ping=True`. La app usa la URL *pooled*; Alembic usa la URL directa.
- La sesión se abre por request en `get_db`; commit al final si no hubo error, rollback si lo hubo. Los repositorios no hacen commit.
- Enviar un examen usa `SELECT ... FOR UPDATE` sobre el examen para evitar doble envío.

## Integración con Gemini

- Solo en `app/infrastructure/gemini.py`, detrás del puerto `DiagnosisGenerator`.
- Usar salida estructurada (`response_mime_type="application/json"` + schema) y validar la respuesta con Pydantic.
- *Timeout* explícito. Si Gemini falla o responde algo inválido: registrar el error, devolver los puntajes con `diagnosis: null` y permitir regenerar. Nunca perder los puntajes por un fallo de la IA.
- Modelo configurable con `GEMINI_MODEL`. El *prompt* va en español.
- Las pruebas nunca llaman a la API real: usan un `FakeDiagnosisGenerator`.

## API

- Prefijo `/api/v1`. Recursos en plural y en inglés (`/students`, `/exams`).
- Errores de dominio → HTTP en `presentation/errors.py`: no encontrado → 404, estado inválido → 409, datos inválidos → 422.
- Cuerpo de error uniforme: `{"detail": "<mensaje en español>"}`.
- Cada endpoint declara `response_model`.

## Convenciones de código

- Código e identificadores en **inglés**, salvo los modelos ORM, que reflejan la BD en español. Mensajes al usuario, *prompt* de Gemini y documentación en **español**.
- PEP 8, *type hints* en todas las funciones públicas, `snake_case` para funciones/variables, `PascalCase` para clases.
- Comentarios solo para explicar el *por qué*, no el *qué*.
- Sin `print` en el código de la app: usar `logging`.

## Pruebas

- `pytest`. Obligatorio probar: calificación (`scoring.py`), reglas de generación del examen (10/10/10, sin repetidas), que el examen no expone la respuesta correcta, doble envío (409), opción que no pertenece a la pregunta (422), fallo de Gemini (puntajes conservados), login (credenciales malas, token inválido/vencido → 401), correo duplicado y acceso a un examen ajeno (404).
- Las pruebas nunca escriben en la base de datos de Neon donde está el banco real: usar una BD o *branch* de Neon separada para pruebas de integración.
- Pruebas de dominio sin BD; casos de uso con *fakes*; API con `TestClient`.
- Ejecutar `pytest` antes de dar algo por terminado e informar el resultado real.

## Flujo de trabajo

- Trabajar por fases; al terminar una, detenerse y esperar instrucciones.
- Antes de programar una funcionalidad, confirmar que está en PROJECT_PLAN.md.
- Cambios pequeños y enfocados; no refactorizar código ajeno a la tarea.
- Commits en español, en imperativo y descriptivos (`Agrega cálculo de puntaje por componente`).

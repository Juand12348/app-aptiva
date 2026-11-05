# Aptiva AI — Plan del proyecto (backend)

> Sistema de evaluación diagnóstica de matemáticas con análisis generado por Google Gemini.
> Equipo: 4 integrantes · Plazo: 2 semanas · Stack: Python, FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL (Neon), Gemini API.
> Alcance de este repositorio: **solo backend** (API REST).

---

## 1. Análisis de requisitos

### 1.1 Requisitos funcionales

| ID | Requisito | Módulo |
|----|-----------|--------|
| RF-01 | Banco con ≥150 preguntas: 50 Estadística, 50 Geometría, 50 Cálculo y Álgebra (lo carga el equipo de BD en las tablas existentes de Neon) | `question_bank` |
| RF-02 | Cada pregunta tiene 4 opciones y exactamente 1 correcta | `question_bank` |
| RF-03 | Cada pregunta tiene dificultad: Fácil, Medio o Difícil | `question_bank` |
| RF-04 | Generar examen de 30 preguntas: 10 aleatorias por componente, sin repetir | `exams` |
| RF-05 | Registrar las respuestas del estudiante | `exams` |
| RF-06 | Calcular puntaje global (/30) y por componente (/10) | `exams` |
| RF-07 | Enviar a Gemini los resultados calculados por el backend | `diagnosis` |
| RF-08 | Gemini genera fortalezas, debilidades y recomendaciones | `diagnosis` |
| RF-09 | Guardar los diagnósticos en PostgreSQL | `diagnosis` |
| RF-10 | Exponer los datos del dashboard: puntaje global, por componente, desglose para gráficos, fortalezas/debilidades, recomendaciones | `exams` + `diagnosis` |
| RF-11 | Consultar el historial de evaluaciones del estudiante | `exams` |
| RF-12 | Registro e inicio de sesión del estudiante (correo + contraseña); cada estudiante solo accede a sus propios exámenes | `auth` |

### 1.2 Requisitos no funcionales

- **Arquitectura:** Clean Architecture con 4 capas (Presentation, Application, Domain, Infrastructure).
- **Integridad:** las reglas del banco (4 opciones, 1 correcta) se garantizan con restricciones en la base de datos.
- **Seguridad:** contraseñas con hash (Argon2); sesión con JWT; la respuesta correcta nunca se envía al cliente antes de calificar; un estudiante no puede ver ni enviar exámenes ajenos. Secretos solo en variables de entorno.
- **Privacidad:** a Gemini se envían solo puntajes, nunca nombre ni correo del estudiante.
- **Resiliencia:** si Gemini falla, el examen y sus puntajes ya están guardados; el diagnóstico se puede regenerar.
- **Realismo:** alcance ejecutable por 4 estudiantes en 2 semanas.

### 1.3 Decisiones confirmadas

1. **"Adaptativo"** se refiere al diagnóstico personalizado. Selección de preguntas 100 % aleatoria por componente, sin ajustar dificultad.
2. **Distribución de dificultad:** aleatoria pura dentro de cada componente.
3. **Login:** sí. Registro con nombre, correo y contraseña; inicio de sesión que devuelve un JWT. Un solo rol (estudiante).
4. **Frontend:** fuera de este repositorio por ahora. El backend expone los datos del dashboard listos para graficar.
5. **Banco de preguntas:** lo carga el equipo de BD en las tablas existentes de Neon (hoy vacías). El backend no incluye seed ni CRUD de preguntas.
6. **Envío de respuestas:** las 30 respuestas en una sola petición al finalizar. Sin responder = incorrecta.

### 1.4 Esquema existente

El esquema completo ya existe en Neon (9 tablas, nombres en español) y es la fuente de verdad. El backend se adapta a él; ver §5.

### 1.5 Fuera de alcance (no se construye)

Frontend, roles/administración, recuperación de contraseña, *refresh tokens*, verificación de correo, CRUD o seed de preguntas, examen adaptativo por dificultad, temporizador, guardado parcial de respuestas, colas o *workers*, caché, despliegue.

---

## 2. Arquitectura técnica

### 2.1 Vista general

```
Cliente (Swagger UI / futuro frontend)
        │ HTTP/JSON + Authorization: Bearer <JWT>
        ▼
┌──────────────────────────────────────────────┐
│ PRESENTATION   FastAPI routers + schemas     │  ← valida entrada, resuelve usuario actual, errores → HTTP
├──────────────────────────────────────────────┤
│ APPLICATION    casos de uso                  │  ← orquesta: repositorios + dominio + IA + seguridad
├──────────────────────────────────────────────┤
│ DOMAIN         entidades, reglas, puertos    │  ← Python puro: puntaje, reglas del examen
├──────────────────────────────────────────────┤
│ INFRASTRUCTURE SQLAlchemy, Alembic, Gemini,  │  ← implementa los puertos del dominio
│                hash de contraseñas, JWT      │
└──────────────────────────────────────────────┘
        │                         │
        ▼                         ▼
 PostgreSQL (Neon)          Google Gemini API
```

**Regla de dependencia:** `presentation → application → domain ← infrastructure`.
El dominio no importa FastAPI, SQLAlchemy, Pydantic, el SDK de Gemini ni librerías de seguridad.

### 2.2 Decisiones técnicas

| Decisión | Elección | Motivo |
|----------|----------|--------|
| Python | 3.12 | Estable, soportado por todas las librerías |
| ORM | SQLAlchemy 2.x **síncrono** | Más simple que async; FastAPI ejecuta endpoints `def` en un *threadpool*. Carga baja. |
| Driver | `psycopg` 3 (`postgresql+psycopg://`) | Driver moderno, compatible con Neon y SSL |
| Migraciones | Alembic | Obligatorio; esquema versionado |
| Configuración | `pydantic-settings` + `.env` | Validación de variables al arrancar |
| Hash de contraseñas | `pwdlib[argon2]` | Recomendado actualmente por la documentación de FastAPI; `passlib` está sin mantenimiento |
| Tokens | `PyJWT`, HS256, expiración 60 min, sin *refresh* | Lo mínimo para sesión *stateless* |
| Login | `OAuth2PasswordBearer` + formulario (`python-multipart`) | Habilita el botón *Authorize* de Swagger para probar |
| IA | SDK `google-genai` con salida estructurada (JSON schema) | JSON validable con Pydantic, sin parsear texto libre |
| Modelo Gemini | Configurable (`GEMINI_MODEL`), por defecto un modelo *flash* | Rápido y dentro del nivel gratuito |
| Llamada a Gemini | Síncrona con *timeout* | Sin colas; si falla se regenera con un endpoint |
| Puntajes por componente | Se derivan de `detalle_intento` con `GROUP BY id_componente` | La tabla ya guarda `id_componente` y `es_correcta` por pregunta; no hace falta otra tabla |
| Nombres | Modelos ORM con los nombres reales en español; dominio, casos de uso y API en inglés | El ORM refleja la BD tal cual; el repositorio traduce |
| Pruebas | `pytest` + `TestClient`; Gemini simulado | Rápidas y sin costo |

### 2.3 Flujo principal

```
1. POST /auth/register                 → crea estudiante (contraseña con hash)
2. POST /auth/login                    → devuelve access_token (JWT)
   — todo lo siguiente requiere el token —
3. POST /exams                         → 10+10+10 preguntas al azar; examen "En progreso";
                                          devuelve 30 preguntas SIN la correcta
4. POST /exams/{id}/submit {answers}   → valida dueño y opciones, califica, guarda respuestas y puntajes,
                                          marca "Finalizado", llama a Gemini, guarda diagnóstico
                                          (si Gemini falla: puntajes + diagnosis = null)
5. GET  /exams/{id}/result             → datos del dashboard
6. POST /exams/{id}/diagnosis          → regenera diagnóstico si falló
7. GET  /students/me/exams             → historial
```

---

## 3. Módulos y responsabilidades

| Módulo | Responsabilidad | No hace |
|--------|-----------------|---------|
| `auth` | Registro, login, hash/verificación de contraseña, emisión y validación de JWT, resolver el estudiante actual | Roles, recuperación de contraseña |
| `students` | Datos del estudiante (`/students/me`) | Autenticación (la hace `auth`) |
| `question_bank` | Mapear las tablas del banco existentes en Neon; consultar preguntas al azar por componente | Crear o editar preguntas |
| `exams` (motor de evaluación) | Generar examen, recibir respuestas, calificar, puntaje global y por componente, historial | Llamar a Gemini directamente |
| `diagnosis` | Armar el resumen de resultados, llamar a Gemini, validar la respuesta, guardar el diagnóstico | Calcular puntajes |
| `core` (transversal) | Configuración, sesión de BD, errores comunes | Lógica de negocio |

### 3.1 Contenido por capa

| Capa | Contenido |
|------|-----------|
| **Domain** | Entidades (`dataclass`): `Student`, `Question`, `Option`, `Exam`, `ExamQuestion`, `ComponentScore`, `Diagnosis`. Enum `ExamStatus`. La dificultad es el nombre leído de `niveles_dificultad`. Funciones puras de calificación. Puertos (`Protocol`): repositorios, `DiagnosisGenerator`, `PasswordHasher`, `TokenService`. Excepciones de dominio. |
| **Application** | Casos de uso: `RegisterStudent`, `Login`, `StartExam`, `SubmitExam`, `GenerateDiagnosis`, `GetExamResult`, `ListStudentExams`. |
| **Infrastructure** | Modelos ORM, repositorios SQLAlchemy, `GeminiDiagnosisGenerator`, `Argon2PasswordHasher`, `JwtTokenService`, `Settings`, `engine`/`SessionLocal`, migraciones Alembic. |
| **Presentation** | Routers, schemas Pydantic, `dependencies.py` (sesión, `get_current_student`, armado de casos de uso), *exception handlers*. |

---

## 4. Dependencias entre módulos

```
auth ──► students ◄── exams ──► question_bank
                        │
                        ▼
                    diagnosis ──► (puerto) DiagnosisGenerator ◄── infrastructure/gemini
```

- `auth` depende de `students` (busca y crea estudiantes).
- `exams` depende de `question_bank` (selección) y de `students` (dueño). Todos sus endpoints usan `get_current_student` de `auth`.
- `diagnosis` depende de `exams` (lee puntajes). `exams` no depende de `diagnosis`: el caso de uso `SubmitExam` invoca `GenerateDiagnosis` después de guardar los puntajes.
- En la BD, `componentes` pertenece a `materias`. Solo hay una materia (Matemáticas); el backend no expone materias.
- Ningún caso de uso depende de Gemini, Argon2 ni PyJWT directamente: solo de sus puertos.

**Orden de construcción:** `core` → `question_bank` + `students` → `auth` → `exams` → `diagnosis` → historial/dashboard.

---

## 5. Modelo de datos (PostgreSQL)

### 5.1 Esquema existente en Neon (fuente de verdad)

```
materias            (id_materia PK, nombre UNIQUE, descripcion)
componentes         (id_componente PK, id_materia FK, nombre, descripcion)
niveles_dificultad  (id_nivel PK, nombre UNIQUE, descripcion)
preguntas           (id_pregunta PK, id_componente FK, id_nivel FK, enunciado, activa)
opciones_respuesta  (id_opcion PK, id_pregunta FK, texto_opcion, es_correcta)
estudiantes         (id_estudiante PK, nombre, correo UNIQUE)
intentos_examen     (id_intento PK, id_estudiante FK, fecha_inicio, fecha_fin, puntaje_total, estado)
detalle_intento     (id_detalle PK, id_intento FK, id_pregunta, id_componente, id_opcion_seleccionada,
                     orden, es_correcta)
diagnosticos_ia     (id_diagnostico PK, id_intento UNIQUE FK, fortalezas, debilidades,
                     recomendaciones, fecha_generacion)
```

### 5.2 Correspondencia con los requisitos

| Requisito | Cómo lo cubre el esquema | Qué hace el backend |
|-----------|--------------------------|---------------------|
| 10 por componente | — | `ORDER BY random() LIMIT 10` por componente, solo `activa = TRUE`; el caso de uso verifica que salieron 10 |
| Sin repetidas | `UNIQUE (id_intento, id_pregunta)` | — |
| Orden 1–30 | `UNIQUE (id_intento, orden)` + `CHECK (orden BETWEEN 1 AND 30)` | Asigna 1..30 |
| Opción elegida pertenece a la pregunta | FK compuesta `(id_opcion_seleccionada, id_pregunta)` | Además valida antes, para responder 422 en lugar de un error de BD |
| Componente de la pregunta coherente | FK compuesta `(id_pregunta, id_componente)` | Copia `id_componente` desde la pregunta |
| Puntaje global /30 | `CHECK (puntaje_total BETWEEN 0 AND 30)` | Lo calcula y guarda al enviar |
| Puntaje por componente /10 | `detalle_intento.id_componente` + `es_correcta` | `GROUP BY id_componente`; no se crea tabla nueva |
| Estados | `CHECK (estado IN ('En progreso','Finalizado','Cancelado'))` | Usa `En progreso → Finalizado`. `Cancelado` no se usa (fuera de alcance) |
| Un diagnóstico por examen | `UNIQUE (id_intento)` | Regenerar = actualizar la fila existente |
| Dificultad | Tabla `niveles_dificultad` | Se lee el nombre; el enum del dominio se mapea a los nombres reales |
| 4 opciones, 1 correcta | "Se validan mediante triggers" (según el comentario del script) | Prueba de integración de solo lectura que lo verifica |

### 5.3 Brechas y migración necesaria

Lo que falta para cumplir el alcance confirmado:

1. **Login (confirmado):** `estudiantes` no tiene columna de contraseña y `correo` admite `NULL`. Las tablas están vacías, así que la única migración del proyecto es directa:
   - `ADD COLUMN contrasena_hash VARCHAR(255) NOT NULL`
   - `ALTER COLUMN correo SET NOT NULL`
2. **Diagnóstico en `TEXT`:** fortalezas, debilidades y recomendaciones son `TEXT`, no listas. **Decisión:** se guarda un elemento por línea (`"\n".join(...)`) y se separa al leer. Es legible en la BD y no obliga a cambiar el esquema.

No se crean tablas nuevas.

### 5.4 Alembic con un esquema existente

1. Mapear los modelos ORM a las 9 tablas con los nombres exactos.
2. Crear una migración `0001_baseline` vacía y marcarla con `alembic stamp 0001_baseline` (no la ejecuta; solo registra que el esquema ya existe).
3. `0002_student_password`: los cambios de §5.3.1.
4. El *autogenerate* se revisa línea por línea: si los modelos no coinciden con la BD, propondrá borrar o modificar tablas reales.

### 5.5 Estado actual y verificaciones

Las 9 tablas existen y están **vacías**. El banco (materias, componentes, niveles y 150 preguntas con sus opciones) lo carga el equipo de BD más adelante.

- **Día 1 (solo lectura):** comprobar si existen los triggers de "4 opciones / 1 correcta" (`information_schema.triggers`).
- **El backend no depende de nombres fijos de componentes ni de niveles:** los lee de la BD y los muestra tal cual. Por eso no hay enum `Difficulty` en el dominio.
- **Mientras no esté cargado el banco:** las pruebas usan datos de ejemplo insertados en la *branch* de pruebas (3 componentes × 10+ preguntas).
- **Al cargar el banco:** correr la prueba de integración de solo lectura: 3 componentes, ≥50 preguntas activas por componente, 4 opciones y 1 correcta por pregunta.

---

## 6. API (contrato inicial)

| Método | Ruta | Auth | Descripción |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | — | Registrar estudiante (nombre, correo, contraseña ≥ 8) |
| POST | `/api/v1/auth/login` | — | Login (formulario OAuth2) → `{access_token, token_type}` |
| GET | `/api/v1/students/me` | ✔ | Datos del estudiante actual |
| GET | `/api/v1/students/me/exams` | ✔ | Historial: fecha, puntaje global, puntajes por componente |
| POST | `/api/v1/exams` | ✔ | Iniciar examen (30 preguntas, sin respuesta correcta) |
| POST | `/api/v1/exams/{exam_id}/submit` | ✔ | Enviar respuestas → puntajes (+ diagnóstico si Gemini responde) |
| GET | `/api/v1/exams/{exam_id}/result` | ✔ | Datos del dashboard: global, por componente, por dificultad, diagnóstico |
| POST | `/api/v1/exams/{exam_id}/diagnosis` | ✔ | Regenerar diagnóstico |
| GET | `/health` | — | Estado de la API y de la conexión a la BD |

- Las rutas usan `me` en lugar de `{student_id}`: el estudiante sale del token, así no se puede pedir el historial de otro.
- Un examen de otro estudiante responde **404** (no 403), para no revelar que existe.
- Login fallido: mensaje genérico "Correo o contraseña incorrectos", sin indicar cuál falló.

Datos enviados a Gemini (sin datos personales):

```json
{
  "total_score": 21, "max_total": 30,
  "components": [
    {"component": "Estadística", "score": 8, "max": 10,
     "by_difficulty": {"easy": "4/4", "medium": "3/4", "hard": "1/2"}}
  ]
}
```

Respuesta esperada (validada con Pydantic): `{"strengths": [str], "weaknesses": [str], "recommendations": [str]}`.

---

## 7. Estructura de carpetas

```
aptiva-backend/
├── app/
│   ├── main.py                     # crea la app, registra routers y handlers
│   ├── domain/
│   │   ├── entities.py             # dataclasses y enums
│   │   ├── scoring.py              # funciones puras de calificación
│   │   ├── ports.py                # Protocols: repositorios, DiagnosisGenerator, PasswordHasher, TokenService
│   │   └── exceptions.py
│   ├── application/
│   │   ├── auth.py                 # RegisterStudent, Login
│   │   ├── exams.py                # StartExam, SubmitExam, GetExamResult, ListStudentExams
│   │   └── diagnosis.py            # GenerateDiagnosis
│   ├── infrastructure/
│   │   ├── config.py               # Settings
│   │   ├── database.py             # engine, SessionLocal
│   │   ├── models.py               # modelos ORM
│   │   ├── repositories.py         # implementaciones SQLAlchemy
│   │   ├── security.py             # Argon2PasswordHasher, JwtTokenService
│   │   └── gemini.py               # GeminiDiagnosisGenerator
│   └── presentation/
│       ├── dependencies.py         # get_db, get_current_student, armado de casos de uso
│       ├── errors.py               # dominio → HTTP
│       ├── schemas.py              # Pydantic request/response
│       └── routers/
│           ├── auth.py
│           ├── students.py
│           └── exams.py
├── alembic/                        # env.py + versions/
├── alembic.ini
├── tests/
│   ├── domain/                     # calificación y reglas (sin BD)
│   ├── application/                # casos de uso con fakes
│   └── api/                        # endpoints con TestClient
├── .env.example
├── requirements.txt
├── README.md
├── PROJECT_PLAN.md
└── CLAUDE.md
```

Un archivo por capa y módulo. Si uno pasa de ~300 líneas se divide en paquete; no antes.

---

## 8. Riesgos técnicos

| # | Riesgo | Impacto | Mitigación |
|---|--------|---------|------------|
| R1 | **Alembic *autogenerate* propone borrar o alterar tablas reales** porque un modelo no coincide con la BD | Alto | Migración base + `stamp`; revisar cada migración generada a mano; no ejecutar `upgrade` contra Neon sin revisión |
| R2 | **Datos del banco con errores** (2 correctas, 3 opciones, conteos ≠ 50) o triggers ausentes | Alto | Verificaciones de §5.5; prueba de integración de solo lectura |
| R2b | **El banco se carga tarde** y bloquea las pruebas reales del examen | Medio | Datos de ejemplo en la *branch* de pruebas desde el día 1; fecha límite de carga: fin de la semana 1 |
| R3 | **Gemini devuelve formato inválido** | Medio | Salida estructurada + validación Pydantic; `diagnosis = null` y regeneración |
| R4 | **Cuota / latencia de Gemini** (nivel gratuito) | Medio | *Timeout* ~20 s; una llamada por examen; *fake* en pruebas |
| R5 | **Neon:** suspensión por inactividad y cierre de conexiones ociosas | Medio | `pool_pre_ping`, `pool_recycle`, `sslmode=require`; URL *pooled* para la app y directa para Alembic |
| R6 | **Acceso a exámenes ajenos** (IDOR) | Alto | Todo caso de uso de examen filtra por `student_id` del token; prueba específica |
| R7 | **Fuga de la respuesta correcta** | Alto | Schemas separados sin `is_correct`; prueba que lo verifica |
| R8 | **`JWT_SECRET_KEY` débil o versionado** | Alto | Secreto aleatorio largo (`secrets.token_urlsafe(32)`) en `.env`; la app no arranca sin él |
| R9 | **Doble envío del mismo examen** | Medio | `SELECT ... FOR UPDATE` + exigir `estado = 'En progreso'`; segundo envío → 409 |
| R10 | **Conflictos de migraciones** entre 4 personas | Medio | Una persona dueña de modelos/migraciones en la semana 1; revisar `alembic heads` |
| R11 | **Sobreingeniería de Clean Architecture** | Medio | Reglas en CLAUDE.md: puertos solo para dependencias externas reales |
| R12 | **Diagnóstico genérico** | Bajo | Desglose por componente y dificultad; *prompt* concreto en español |

---

## 9. Plan de trabajo (2 semanas, 4 integrantes)

**Roles:** A = Infraestructura y BD · B = Motor de evaluación · C = IA (Gemini) · D = Autenticación + historial/dashboard.

### Semana 1 — Base, auth y motor

| Día | A | B | C | D |
|-----|---|---|---|---|
| 1 | Repo, `requirements`, config, conexión a Neon; verificaciones de §5.5; crear *branch* de Neon para pruebas | Entidades y enums del dominio | API key de Gemini; prueba aislada del SDK | Puertos `PasswordHasher` y `TokenService` |
| 2–3 | Modelos ORM sobre las 9 tablas; `0001_baseline` + `stamp`; `0002_student_password` | `scoring.py` + pruebas unitarias | Puerto `DiagnosisGenerator` + *fake*; diseño del *prompt* | `security.py` (Argon2, JWT) + pruebas |
| 4–5 | Repositorios SQLAlchemy; prueba de verificación del banco | `StartExam` y `SubmitExam` | `GeminiDiagnosisGenerator` con salida estructurada | `RegisterStudent`, `Login`, `get_current_student`, routers de auth |

**Hito semana 1:** registro/login funcionando; examen generable y calificable desde los casos de uso.

### Semana 2 — IA, dashboard y cierre

| Día | A | B | C | D |
|-----|---|---|---|---|
| 6–7 | Restricciones finales; `/health` | Endpoints de exámenes | `GenerateDiagnosis` + guardado + endpoint de regeneración | `GET /result` y `/students/me/exams` |
| 8–9 | Pruebas contra Neon real | Pruebas de API (doble envío, opción inválida, examen ajeno) | Ajuste del *prompt* con resultados reales | Pruebas de auth (token vencido/inválido, correo duplicado) |
| 10 | README, `.env.example` | Corrección de errores | Corrección de errores | Recorrido completo en Swagger para la demo |

**Hito final:** flujo completo registro → login → examen → resultado → diagnóstico → historial.

---

## 10. Criterios de aceptación

- [ ] Alembic queda marcado sobre el esquema existente y `0002_student_password` se aplica sin tocar ninguna otra tabla.
- [ ] La verificación del banco confirma 50/50/50, 4 opciones y 1 correcta por pregunta.
- [ ] Registro y login funcionan; las contraseñas se guardan con hash; los endpoints protegidos rechazan peticiones sin token o con token inválido (401).
- [ ] Un estudiante no puede ver ni enviar exámenes de otro (404).
- [ ] `POST /exams` devuelve 30 preguntas distintas, 10 por componente, sin la respuesta correcta.
- [ ] `submit` calcula el puntaje global (/30) y por componente (/10) correctamente (cubierto por pruebas).
- [ ] El diagnóstico se guarda en `diagnoses`; si Gemini falla, los puntajes se conservan y el diagnóstico se puede regenerar.
- [ ] El historial lista todos los exámenes del estudiante con sus puntajes.
- [ ] Ningún secreto en el repositorio.

# Documentación del Backend — Dashboard LDT

## Índice

1. [¿Qué es este sistema?](#1-qué-es-este-sistema)
2. [Tecnologías utilizadas](#2-tecnologías-utilizadas)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Base de datos: tablas y relaciones](#4-base-de-datos-tablas-y-relaciones)
5. [Cómo se comunica la API con la base de datos](#5-cómo-se-comunica-la-api-con-la-base-de-datos)
6. [Módulos (rutas) de la API](#6-módulos-rutas-de-la-api)
7. [Autenticación y seguridad](#7-autenticación-y-seguridad)
8. [Roles y permisos](#8-roles-y-permisos)
9. [Despliegue (Vercel)](#9-despliegue-vercel)
10. [Guía de mantenimiento](#10-guía-de-mantenimiento)
11. [Variables de entorno requeridas](#11-variables-de-entorno-requeridas)
12. [Glosario](#12-glosario)

---

## 1. ¿Qué es este sistema?

Este backend es la capa lógica del **Dashboard LDT**, una aplicación web de gestión para una iglesia. Su función principal es:

- Almacenar y gestionar información de **alumnos**, **maestros** y **pastores**.
- Controlar el seguimiento espiritual de cada alumno a través de **estados** y **bolsas**.
- Registrar la actividad del sistema: cambios de estado y observaciones/comentarios.
- Exponer todos estos datos a través de una **API REST** que consume el frontend.

---

## 2. Tecnologías utilizadas

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.11+ |
| Framework de API | FastAPI |
| Base de datos | PostgreSQL (alojada en Supabase) |
| ORM (comunicación con BD) | SQLAlchemy |
| Autenticación | JWT (tokens) + Supabase Auth |
| Almacenamiento de archivos | Supabase Storage (fotos de perfil) |
| Despliegue | Vercel (serverless) |
| Gestión de dependencias | Poetry |

---

## 3. Estructura del proyecto

```
dashboard_ldt_back/
├── api/
│   └── index.py          → Punto de entrada para Vercel
├── app/
│   ├── main.py           → Configuración principal de la aplicación
│   ├── core/
│   │   ├── config.py     → Variables de entorno y configuración
│   │   └── security.py   → Creación de tokens JWT y hashing de contraseñas
│   ├── database/
│   │   ├── base.py       → Clase base para los modelos de BD
│   │   └── connection.py → Conexión con PostgreSQL
│   ├── models/           → Definición de las tablas de la base de datos
│   ├── schemas/          → Validación de los datos que entran y salen de la API
│   ├── routes/           → Endpoints de la API (uno por módulo)
│   ├── services/         → Lógica de negocio reutilizable
│   ├── dependencies/     → Inyección de dependencias (BD, usuario autenticado)
│   └── integrations/     → Conexión con servicios externos (Supabase)
├── docs/                 → Documentación del proyecto
├── pyproject.toml        → Dependencias del proyecto
└── vercel.json           → Configuración de despliegue
```

---

## 4. Base de datos: tablas y relaciones

### Diagrama conceptual de relaciones

```
roles ──────────────────────────────────────────────────┐
perfiles ───────────────────┐                           │
                            ▼                           │
                        personas ◄──────────────────────┘
                       /    |    \                  (person_roles)
                      /     |     \
               maestros  alumnos  [autor de observaciones]
                  │         │
                  │         ├── observaciones
                  │         ├── historial_estados
                  │         └── tarjetas
                  │                  │
                  └──────────────────┘
                           │
                        estados ──── bolsas
```

### Descripción de cada tabla

#### `personas`
La tabla central del sistema. Representa a cualquier persona registrada (alumno, maestro o pastor).

| Campo | Descripción |
|---|---|
| `id_persona` | Identificador único (UUID) |
| `auth_user_id` | ID del usuario en Supabase Auth |
| `nombre` | Nombre de la persona |
| `apellido` | Apellido de la persona |
| `email` | Correo electrónico |
| `password` | Contraseña hasheada (solo si no usa Supabase) |
| `foto_url` | URL de la foto de perfil |
| `id_perfil` | Referencia al perfil de acceso |

---

#### `perfiles`
Define el **nivel de acceso** al sistema.

| Campo | Descripción |
|---|---|
| `id_perfil` | Identificador numérico |
| `descripcion` | Nombre del perfil (ej. "Administrador") |
| `nivel_acceso` | Número que indica privilegios: 1 = Admin, 2 = Moderador, 3 = Usuario |

---

#### `roles`
Describe el **rol funcional** de una persona dentro de la iglesia.

| Campo | Descripción |
|---|---|
| `id_rol` | Identificador numérico |
| `descripcion` | Nombre del rol (ej. "Pastor", "Maestro") |

> Un usuario puede tener más de un rol. La relación se guarda en la tabla `person_roles`.

---

#### `person_roles`
Tabla intermedia que asocia personas con sus roles.

| Campo | Descripción |
|---|---|
| `person_id` | ID de la persona |
| `id_rol` | ID del rol asignado |

---

#### `maestros`
Información adicional exclusiva de los maestros.

| Campo | Descripción |
|---|---|
| `id_maestro` | Identificador único (UUID) |
| `id_persona` | Referencia a la tabla `personas` |
| `telefono` | Teléfono de contacto |
| `direccion` | Dirección física |

---

#### `alumnos`
Información adicional exclusiva de los alumnos.

| Campo | Descripción |
|---|---|
| `id_alumno` | Identificador único (UUID) |
| `id_persona` | Referencia a la tabla `personas` |
| `dias` | Días disponibles (almacenado en formato JSON) |
| `franja_horaria` | Horario preferido |
| `motivo_oracion` | Petición de oración del alumno |
| `id_estado_actual` | Estado espiritual actual del alumno |

---

#### `bolsas`
Agrupa estados dentro de una categoría o etapa de seguimiento (ej. "Bienvenida", "Discipulado").

| Campo | Descripción |
|---|---|
| `id_bolsa` | Identificador único (UUID) |
| `nombre` | Nombre de la bolsa |
| `descripcion` | Descripción del propósito de la bolsa |
| `estados_orden` | Lista ordenada de estados que pertenecen a la bolsa |

---

#### `estados`
Representa cada paso o etapa individual del proceso de seguimiento del alumno.

| Campo | Descripción |
|---|---|
| `id_estado` | Identificador numérico |
| `nombre` | Nombre del estado (ej. "Primera visita", "Bautizado") |
| `orden` | Posición del estado dentro de su bolsa |
| `activo` | Si el estado está habilitado para uso |
| `id_bolsa` | A qué bolsa pertenece este estado |

---

#### `tarjetas`
Representa la "ficha de seguimiento" de un alumno. Conecta al alumno con su maestro asignado y su estado actual.

| Campo | Descripción |
|---|---|
| `id_tarjeta` | Identificador único (UUID) |
| `id_alumno` | Alumno al que pertenece la tarjeta |
| `id_estado_actual` | Estado espiritual actual |
| `id_maestro_asignado` | Maestro responsable de este alumno |

---

#### `historial_estados`
Registro completo de todos los cambios de estado de los alumnos.

| Campo | Descripción |
|---|---|
| `id_historial` | Identificador único (UUID) |
| `id_alumno` | Alumno que cambió de estado |
| `id_estado` | Nuevo estado asignado |
| `comentario` | Comentario opcional del cambio |
| `fecha_cambio` | Fecha y hora del cambio |
| `cambiado_por` | Persona que realizó el cambio |

---

#### `observaciones`
Comentarios o anotaciones sobre un alumno, escritos por maestros o pastores.

| Campo | Descripción |
|---|---|
| `id_observacion` | Identificador único (UUID) |
| `id_alumno` | Alumno sobre el que se escribe |
| `id_autor` | Persona que escribió la observación |
| `texto` | Contenido de la observación |
| `created_at` | Fecha de creación |

---

## 5. Cómo se comunica la API con la base de datos

El sistema usa **SQLAlchemy** como intermediario entre el código Python y la base de datos PostgreSQL. Este patrón funciona de la siguiente manera:

1. **Al iniciar la aplicación**, se establece una conexión con la base de datos usando la URL configurada en las variables de entorno (`DATABASE_URL`).
2. **Cada petición HTTP** que llega al servidor abre una sesión de base de datos temporal (a través del mecanismo de dependencias de FastAPI).
3. **Dentro de cada endpoint**, el código realiza consultas usando objetos Python que representan las tablas (llamados *modelos*), sin necesidad de escribir SQL directamente.
4. **Al finalizar la petición**, la sesión se cierra automáticamente.

Este enfoque garantiza que:
- No se queden conexiones abiertas innecesariamente.
- Los errores en una operación no afecten otras solicitudes.
- Los datos se devuelvan en formato JSON al frontend.

### Flujo típico de una petición

```
Frontend (React) → Petición HTTP → API (FastAPI) → SQLAlchemy → PostgreSQL (Supabase)
                ←  Respuesta JSON ←               ←           ←
```

---

## 6. Módulos (rutas) de la API

Todos los endpoints requieren autenticación mediante token JWT en el encabezado `Authorization: Bearer <token>`, salvo los de login y registro.

### `/auth` — Autenticación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/login` | Inicia sesión con email y contraseña. Devuelve un token JWT. |
| POST | `/auth/register` | Registra un nuevo usuario en el sistema. |
| GET | `/auth/me` | Devuelve los datos del usuario actualmente autenticado. |
| POST | `/auth/logout` | Cierra la sesión (el token se invalida en el cliente). |

---

### `/alumnos` — Gestión de alumnos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/alumnos` | Lista alumnos. Un pastor ve todos; un maestro solo los suyos. |
| POST | `/alumnos` | Registra un nuevo alumno. |
| GET | `/alumnos/{id}` | Obtiene el detalle de un alumno específico. |
| PUT | `/alumnos/{id}` | Actualiza los datos de un alumno. |
| DELETE | `/alumnos/{id}` | Elimina un alumno del sistema. |
| PATCH | `/alumnos/{id}/estado` | Cambia el estado espiritual de un alumno y registra el cambio en el historial. |
| GET | `/alumnos/{id}/historial` | Consulta el historial de cambios de estado de un alumno. |
| POST | `/alumnos/{id}/observaciones` | Agrega una observación/comentario sobre un alumno. |
| GET | `/alumnos/{id}/observaciones` | Lista todas las observaciones de un alumno. |

---

### `/maestros` — Gestión de maestros

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/maestros` | Lista todos los maestros registrados. |
| POST | `/maestros` | Registra un nuevo maestro (crea persona + maestro). |
| GET | `/maestros/{id}` | Obtiene el detalle de un maestro. |
| PUT | `/maestros/{id}` | Actualiza los datos de un maestro. |
| DELETE | `/maestros/{id}` | Elimina un maestro del sistema. |

---

### `/bolsas` — Categorías de seguimiento

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/bolsas` | Lista todas las bolsas configuradas. |
| POST | `/bolsas` | Crea una nueva bolsa. |
| PUT | `/bolsas/{id}` | Actualiza el nombre/descripción de una bolsa. |
| DELETE | `/bolsas/{id}` | Elimina una bolsa. |
| PATCH | `/bolsas/{id}/actividad-nombre` | Cambia el nombre de una actividad dentro de la bolsa. |

---

### `/estados` — Estados espirituales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/estados` | Lista todos los estados disponibles, ordenados. |
| POST | `/estados` | Crea un nuevo estado. |

---

### `/personas` — Datos de personas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/personas` | Lista personas en el sistema. |
| PATCH | `/personas/{id}/foto` | Actualiza la foto de perfil de una persona. |

---

### `/actividad` — Feed de actividad global

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/actividad` | Devuelve un feed combinado de cambios de estado y observaciones recientes, ordenados del más nuevo al más viejo. Soporta filtros por tipo y límite de resultados. |

---

### `/dashboard` — Estadísticas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dashboard/stats` | Estadísticas generales (solo pastor/admin): totales de maestros, alumnos, observaciones y cambios de estado. |
| GET | `/dashboard/maestro/{id}/stats` | Estadísticas detalladas de un maestro específico. |
| GET | `/dashboard/actividad-reciente` | Actividad reciente paginada (6 items por página). |
| GET | `/dashboard/distribucion_estado/{id_persona}` | Distribución de alumnos por estado, agrupada por bolsa. |

---

### `/config` — Configuración del sistema

Endpoints para tareas administrativas como reorganización de estados o configuración de bolsas.

---

## 7. Autenticación y seguridad

El sistema soporta dos modos de autenticación:

### Modo Supabase (producción)
Cuando las variables `SUPABASE_URL` y `SUPABASE_ANON_KEY` están configuradas:
1. El usuario envía su email y contraseña al endpoint `/auth/login`.
2. El servidor valida las credenciales contra **Supabase Auth**.
3. Si son válidas, busca a la persona en la base de datos local y genera un **token JWT** propio.
4. El frontend usa ese token en todas las peticiones siguientes.

### Modo local (desarrollo)
Si Supabase no está configurado, el sistema verifica la contraseña directamente contra la base de datos local (contraseña hasheada con bcrypt).

### Cómo funciona el token JWT
- El token contiene únicamente el ID de usuario (`auth_user_id`).
- No tiene fecha de expiración configurada actualmente (se puede agregar con `ACCESS_TOKEN_EXPIRE_MINUTES`).
- Cada endpoint protegido extrae el ID del token y consulta la base de datos para obtener los datos completos del usuario.

---

## 8. Roles y permisos

El sistema tiene dos niveles de control de acceso que funcionan en conjunto:

### Niveles de acceso (perfiles)
| Nivel | Descripción | Privilegios |
|---|---|---|
| 1 | Administrador | Acceso total, puede ver y modificar todo |
| 2 | Moderador | Acceso intermedio |
| 3 | Usuario | Acceso básico |

### Roles funcionales
| ID | Rol | Qué puede hacer |
|---|---|---|
| 1 | Pastor | Ver todos los alumnos y maestros, todas las estadísticas |
| 2 | Maestro | Ver y gestionar únicamente sus alumnos asignados |

### Reglas de visibilidad principales
- **Administrador (nivel 1)**: ve y puede modificar absolutamente todo sin restricciones.
- **Pastor (rol 1)**: ve todos los alumnos y estadísticas del sistema.
- **Maestro (rol 2)**: solo ve los alumnos que tiene asignados mediante una tarjeta.

---

## 9. Despliegue (Vercel)

La aplicación está configurada para desplegarse en **Vercel** como función serverless:

- El archivo `vercel.json` redirige todas las peticiones al archivo `api/index.py`.
- Este archivo expone la aplicación FastAPI de `app/main.py`.
- Cada petición puede ejecutarse en una instancia separada (sin estado compartido entre peticiones).

**Consideración importante**: En entornos serverless, la conexión con la base de datos se abre y cierra en cada invocación. Por eso el sistema valida la conexión al iniciar (`SELECT 1`) y la cierra al terminar.

---

## 10. Guía de mantenimiento

### Agregar un nuevo endpoint

1. Identificar a qué módulo pertenece (alumnos, maestros, etc.) o crear un nuevo archivo en `app/routes/`.
2. Definir la función con el decorador correspondiente (`@router.get`, `@router.post`, etc.).
3. Agregar el router en `app/main.py` si es un módulo nuevo.
4. Si se necesitan nuevos datos de entrada/salida, crear el esquema en `app/schemas/`.

### Agregar una nueva tabla a la base de datos

1. Crear el modelo en `app/models/nuevo_modelo.py` heredando de `Base`.
2. Ejecutar la migración en PostgreSQL/Supabase (actualmente las migraciones son manuales; no hay herramienta como Alembic configurada).
3. Importar el modelo en los endpoints que lo necesiten.

### Cambiar variables de entorno en producción

Las variables se configuran en el panel de **Vercel** → proyecto → *Settings* → *Environment Variables*. Las variables requeridas son:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

### Verificar que la API está funcionando

- Acceder a `/docs` en el dominio del backend para ver la documentación interactiva generada automáticamente por FastAPI.
- Acceder a `/help` para ver un resumen básico de las rutas disponibles.
- El endpoint raíz no tiene respuesta; usar `/docs` como punto de entrada.

### Monitorear errores

- Los logs de Vercel están disponibles en el panel del proyecto bajo la pestaña *Logs*.
- Los errores de base de datos se imprimen en el log del servidor con el prefijo `[error]`.

### Actualizar dependencias

```bash
# Dentro del directorio del proyecto
poetry update
# Regenerar requirements.txt si es necesario
poetry export -f requirements.txt --output requirements.txt
```

### Correr el proyecto localmente

```bash
# Instalar dependencias
poetry install

# Crear archivo .env con las variables requeridas (ver sección 11)

# Iniciar el servidor
uvicorn app.main:app --reload
```

El servidor estará disponible en `http://localhost:8000` y la documentación en `http://localhost:8000/docs`.

---

## 11. Variables de entorno requeridas

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
# URL de conexión a PostgreSQL (Supabase)
DATABASE_URL=postgresql://usuario:contraseña@host:puerto/nombre_bd

# Clave secreta para firmar los tokens JWT (puede ser cualquier string largo y aleatorio)
JWT_SECRET_KEY=tu_clave_secreta_muy_larga

# Algoritmo JWT (dejar por defecto)
JWT_ALGORITHM=HS256

# Supabase (opcional en desarrollo, requerido en producción)
SUPABASE_URL=https://tu-proyecto.supabase.co
SUPABASE_ANON_KEY=tu_anon_key
SUPABASE_SERVICE_ROLE_KEY=tu_service_role_key

# Nombre del bucket de almacenamiento de fotos
SUPABASE_STORAGE_BUCKET=IGLESIA
```

---

## 12. Glosario

| Término | Significado en el sistema |
|---|---|
| **Alumno** | Persona en proceso de seguimiento espiritual |
| **Maestro** | Líder responsable de un grupo de alumnos |
| **Pastor** | Rol con acceso global a todos los datos del sistema |
| **Bolsa** | Categoría o etapa de seguimiento (agrupa varios estados) |
| **Estado** | Paso específico dentro de una bolsa (ej. "Primera visita") |
| **Tarjeta** | Ficha de seguimiento que vincula un alumno con su maestro y estado actual |
| **Historial de estados** | Registro cronológico de todos los cambios de estado de un alumno |
| **Observación** | Comentario escrito por un maestro o pastor sobre un alumno |
| **JWT** | Token de autenticación que el frontend envía en cada petición |
| **ORM** | Herramienta que permite trabajar con la BD usando código Python en lugar de SQL |
| **Supabase** | Plataforma que provee la base de datos PostgreSQL y el servicio de autenticación |
| **Serverless** | Arquitectura de despliegue donde el servidor se inicia solo cuando llega una petición |

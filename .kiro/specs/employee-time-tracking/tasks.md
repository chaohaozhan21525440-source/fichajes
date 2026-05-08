# Plan de Implementación: Employee Time Tracking

## Visión General

Implementación incremental del sistema de fichaje NFC en tres capas: backend FastAPI (Python), servicio NFC edge (Python) y panel de administración (React + TypeScript). Cada tarea construye sobre la anterior, terminando con la integración completa de todos los componentes.

## Tareas

- [ ] 1. Configurar estructura del proyecto y base de datos
  - Crear estructura de directorios: `backend/`, `nfc_service/`, `frontend/`
  - Crear `backend/alembic.ini` y migraciones iniciales con el esquema PostgreSQL completo (tablas `workers`, `nfc_tokens`, `checkin_records`, `failed_attempts`, `admins`, `audit_log`, `ip_lockouts`)
  - Crear `backend/app/models/` con los modelos SQLAlchemy correspondientes a cada tabla
  - Crear `backend/app/schemas/` con los modelos Pydantic (`Worker`, `NfcToken`, `CheckinRecord`, `FailedAttempt`, `AuditLogEntry`)
  - Crear `backend/requirements.txt` con dependencias fijadas: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg2-binary`, `pydantic`, `python-jose`, `passlib[bcrypt]`, `hypothesis`, `pytest`, `httpx`
  - Crear `backend/app/database.py` con la configuración de conexión a PostgreSQL
  - Aplicar índices de rendimiento definidos en el diseño
  - _Requisitos: 1.1, 1.2, 2.1, 6.1_

- [ ] 2. Implementar autenticación y control de acceso
  - [ ] 2.1 Implementar módulo de autenticación JWT + bcrypt
    - Crear `backend/app/auth/` con funciones de hash de contraseña (`passlib`), generación y validación de JWT (access token 30 min), y dependencia `get_current_admin`
    - Implementar `POST /api/v1/auth/login`: validar credenciales, verificar bloqueo por IP, generar token JWT; mensaje de error genérico en caso de fallo
    - Implementar `POST /api/v1/auth/logout`: invalidar sesión activa
    - Implementar lógica de bloqueo por IP: incrementar contador en `ip_lockouts`, bloquear tras 5 fallos consecutivos durante 15 minutos, resetear contador tras login exitoso
    - _Requisitos: 4.1, 4.2, 4.3, 4.4_

  - [ ]* 2.2 Escribir prueba de propiedad: bloqueo por IP tras intentos fallidos
    - **Propiedad 6: Bloqueo por intentos fallidos de autenticación**
    - Generar con Hypothesis secuencias de intentos fallidos/exitosos para verificar que exactamente 5 fallos consecutivos activan el bloqueo de 15 minutos
    - **Valida: Requisito 4.3**

  - [ ]* 2.3 Escribir prueba de propiedad: mensaje de error genérico en autenticación
    - **Propiedad 12: Mensaje de error genérico en autenticación fallida**
    - Generar con Hypothesis combinaciones de usuario/contraseña incorrectos y verificar que el mensaje de error es siempre idéntico
    - **Valida: Requisito 4.2**

  - [ ]* 2.4 Escribir prueba de propiedad: protección de endpoints con JWT
    - **Propiedad 13: Protección de endpoints con autenticación JWT**
    - Generar con Hypothesis tokens ausentes, malformados, expirados y con firma inválida; verificar que todos los endpoints protegidos devuelven HTTP 401
    - **Valida: Requisito 4.1**

  - [ ]* 2.5 Escribir pruebas unitarias de autenticación
    - Login exitoso, credenciales incorrectas, sesión expirada, bloqueo por IP, acceso con token válido/inválido
    - _Requisitos: 4.1, 4.2, 4.3, 4.4_

- [ ] 3. Implementar gestión de trabajadores
  - [ ] 3.1 Implementar endpoints CRUD de trabajadores
    - Crear `backend/app/routers/workers.py`
    - Implementar `GET /api/v1/workers`: listar trabajadores activos e inactivos
    - Implementar `POST /api/v1/workers`: registrar nuevo trabajador con nombre, `employee_id` y token NFC inicial; registrar en `audit_log`
    - Implementar `PUT /api/v1/workers/{id}`: actualizar datos del trabajador; registrar en `audit_log`
    - Implementar `PATCH /api/v1/workers/{id}/deactivate`: desactivar trabajador conservando histórico; registrar en `audit_log`
    - Implementar `POST /api/v1/workers/{id}/nfc-tokens`: asignar nuevo token NFC; rechazar con 409 si el UID ya está asignado a otro trabajador activo; registrar en `audit_log`
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, 6.2_

  - [ ]* 3.2 Escribir prueba de propiedad: unicidad de token NFC activo
    - **Propiedad 3: Unicidad de token NFC activo**
    - Generar con Hypothesis asignaciones de tokens a múltiples trabajadores y verificar que nunca existe más de un trabajador activo con el mismo UID
    - **Valida: Requisito 2.5**

  - [ ]* 3.3 Escribir prueba de propiedad: conservación de histórico al desactivar
    - **Propiedad 7: Conservación de histórico al desactivar trabajador**
    - Generar con Hypothesis trabajadores con N registros de fichaje, desactivarlos y verificar que los N registros siguen siendo accesibles
    - **Valida: Requisito 2.4**

  - [ ]* 3.4 Escribir prueba de propiedad: completitud del log de auditoría
    - **Propiedad 11: Completitud del log de auditoría**
    - Generar con Hypothesis secuencias de operaciones de gestión (crear, desactivar, asignar token) y verificar que cada operación genera exactamente una entrada en `audit_log` con `admin_id`, tipo de operación y marca de tiempo
    - **Valida: Requisito 6.2**

  - [ ]* 3.5 Escribir pruebas unitarias de gestión de trabajadores
    - Registro de trabajador nuevo, desactivación, asignación de token duplicado (conflicto 409), conservación de histórico tras desactivación
    - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 4. Checkpoint — Verificar autenticación y gestión de trabajadores
  - Asegurarse de que todas las pruebas pasan. Consultar al usuario si surgen dudas.

- [ ] 5. Implementar lógica de fichaje (backend)
  - [ ] 5.1 Implementar endpoint de fichaje individual
    - Crear `backend/app/routers/checkins.py`
    - Implementar `POST /api/v1/checkins`: autenticar dispositivo con Bearer token, buscar trabajador por `nfc_uid` en `nfc_tokens` activos, rechazar con 403 si no existe (insertar en `failed_attempts`), rechazar si trabajador está desactivado, determinar `event_type` consultando el último registro del trabajador (alternancia entrada/salida), insertar en `checkin_records` con `idempotency_key`, devolver `{event_type, worker_name, recorded_at}`
    - _Requisitos: 1.1, 1.2, 1.4, 2.3, 5.1, 5.2, 5.3_

  - [ ]* 5.2 Escribir prueba de propiedad: alternancia correcta del tipo de evento
    - **Propiedad 1: Alternancia correcta del tipo de evento**
    - Generar con Hypothesis historiales de fichaje de longitud variable y verificar que el nuevo evento es siempre el opuesto al último, y que el primer fichaje es siempre `entrada`
    - **Valida: Requisitos 5.1, 5.2, 5.3**

  - [ ]* 5.3 Escribir prueba de propiedad: rechazo de tokens NFC desconocidos con registro
    - **Propiedad 9: Rechazo de tokens NFC desconocidos con registro de intento**
    - Generar con Hypothesis UIDs no registrados y verificar que cada intento devuelve HTTP 403 y crea exactamente un registro en `failed_attempts`
    - **Valida: Requisito 1.4**

  - [ ]* 5.4 Escribir prueba de propiedad: rechazo de fichajes de trabajadores desactivados
    - **Propiedad 10: Rechazo de fichajes de trabajadores desactivados**
    - Generar con Hypothesis trabajadores desactivados con tokens válidos y verificar que ningún intento de fichaje crea un registro válido
    - **Valida: Requisito 2.3**

  - [ ] 5.5 Implementar endpoint de sincronización offline
    - Implementar `POST /api/v1/checkins/sync`: recibir lote de registros, insertar ignorando duplicados por `idempotency_key` (ON CONFLICT DO NOTHING), devolver `{procesados, rechazados}`
    - _Requisitos: 1.5_

  - [ ]* 5.6 Escribir prueba de propiedad: idempotencia de sincronización offline
    - **Propiedad 2: Idempotencia de sincronización offline**
    - Generar con Hypothesis lotes de registros y enviarlos 1–5 veces; verificar que el estado final de la base de datos es idéntico independientemente del número de envíos
    - **Valida: Requisito 1.5**

  - [ ]* 5.7 Escribir prueba de propiedad: inmutabilidad de registros de fichaje
    - **Propiedad 4: Inmutabilidad de registros de fichaje**
    - Generar con Hypothesis registros existentes e intentar operaciones PUT, PATCH y DELETE sobre ellos; verificar que ninguna operación modifica ni elimina registros
    - **Valida: Requisito 6.1**

  - [ ]* 5.8 Escribir pruebas unitarias de fichaje
    - Token válido (entrada y salida), token desconocido (403 + `failed_attempts`), primer fichaje sin historial (entrada), trabajador desactivado (rechazo)
    - _Requisitos: 1.1, 1.4, 2.3, 5.1, 5.2_

- [ ] 6. Implementar consulta, filtrado y exportación CSV
  - [ ] 6.1 Implementar endpoint de consulta de registros con filtros y paginación
    - Implementar `GET /api/v1/checkins?worker_id=&from=&to=&event_type=&page=&size=`: aplicar filtros opcionales, ordenar por `recorded_at` DESC, incluir `worker_name` en cada registro, devolver resultados paginados
    - _Requisitos: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 6.2 Escribir prueba de propiedad: corrección, completitud y orden de consultas
    - **Propiedad 5: Corrección, completitud y orden de las consultas de registros**
    - Generar con Hypothesis conjuntos de registros y combinaciones de filtros; verificar que los resultados satisfacen todos los criterios, no excluyen registros válidos, están ordenados por `recorded_at` DESC e incluyen `worker_name`, `event_type`, fecha y hora con zona horaria
    - **Valida: Requisitos 3.1, 3.2, 3.4**

  - [ ] 6.3 Implementar endpoint de exportación CSV
    - Crear `backend/app/routers/export.py`
    - Implementar `GET /api/v1/export/checkins.csv?worker_id=&from=&to=&event_type=`: aplicar los mismos filtros que la consulta, generar CSV server-side con `csv` stdlib, codificación UTF-8 con BOM, cabeceras: `worker_name`, `employee_id`, `event_type`, `recorded_at`, `device_id`
    - _Requisitos: 3.5_

  - [ ]* 6.4 Escribir prueba de propiedad: fidelidad de exportación CSV
    - **Propiedad 8: Fidelidad de exportación CSV respecto a la consulta**
    - Generar con Hypothesis conjuntos de registros y filtros; verificar que el CSV exportado contiene exactamente los mismos registros que la consulta con los mismos filtros, sin importar la paginación
    - **Valida: Requisito 3.5**

  - [ ] 6.5 Implementar endpoint de auditoría
    - Crear `backend/app/routers/audit.py`
    - Implementar `GET /api/v1/audit?from=&to=&admin_id=`: consultar `audit_log` con filtros opcionales, ordenar por `performed_at` DESC
    - _Requisitos: 6.2_

  - [ ]* 6.6 Escribir pruebas unitarias de consulta y exportación
    - Filtrado por trabajador, rango de fechas y tipo de evento; exportación CSV con formato correcto (columnas, codificación UTF-8, separador); consulta de auditoría
    - _Requisitos: 3.1, 3.2, 3.4, 3.5, 6.2_

- [ ] 7. Checkpoint — Verificar backend completo
  - Asegurarse de que todas las pruebas del backend pasan. Consultar al usuario si surgen dudas.

- [ ] 8. Implementar servicio NFC edge (Python)
  - [ ] 8.1 Crear estructura del servicio NFC y base de datos SQLite local
    - Crear `nfc_service/` con `main.py`, `nfc_reader.py`, `local_store.py`, `sync_service.py`, `config.py`
    - Implementar `local_store.py`: crear tabla `pending_checkins` en SQLite, funciones para insertar registro pendiente (con `idempotency_key` UUID v4), marcar como sincronizado y consultar pendientes
    - _Requisitos: 1.5_

  - [ ] 8.2 Implementar lógica de detección NFC y envío al backend
    - Implementar `nfc_reader.py`: captura de UID mediante librería `keyboard` — el lector USB HID emula teclado y envía el UID seguido de Enter; acumular pulsaciones hasta recibir Enter y devolver el UID como string; incluir stub configurable para pruebas sin hardware
    - Implementar `main.py`: al recibir UID, intentar `POST /api/v1/checkins` con timeout de 2 segundos; si éxito, mostrar confirmación en consola (nombre del trabajador + tipo de evento); si fallo de red o timeout, guardar en SQLite local y mostrar confirmación local
    - Confirmación visual por consola (print con color ANSI) en ≤3 segundos
    - Añadir `keyboard` a `nfc_service/requirements.txt`
    - _Requisitos: 1.1, 1.2, 1.3, 1.5, 5.3_

  - [ ] 8.3 Implementar servicio de sincronización en background
    - Implementar `sync_service.py`: bucle cada 30 segundos, si hay registros pendientes y backend disponible, enviar lote a `POST /api/v1/checkins/sync`, marcar como sincronizados los procesados
    - _Requisitos: 1.5_

  - [ ]* 8.4 Escribir pruebas unitarias del servicio NFC
    - Almacenamiento local cuando backend no disponible, sincronización de pendientes, idempotencia de `idempotency_key`, confirmación en ≤3 segundos
    - _Requisitos: 1.2, 1.3, 1.5_

- [ ] 9. Implementar panel de administración (React + TypeScript)
  - [ ] 9.1 Configurar proyecto React y estructura de páginas
    - Inicializar proyecto con Vite + React 18 + TypeScript en `frontend/`
    - Instalar dependencias: `react-router-dom`, `axios`, `react-query` (o `swr`), librería de componentes UI (p. ej. `shadcn/ui` o similar)
    - Crear estructura de rutas: `/login`, `/` (Dashboard), `/checkins`, `/workers`, `/audit`
    - Crear `frontend/src/api/client.ts`: instancia de axios con base URL, interceptor para adjuntar JWT y redirigir a `/login` en 401
    - _Requisitos: 4.1_

  - [ ] 9.2 Implementar página de login y gestión de sesión
    - Crear `frontend/src/pages/Login.tsx`: formulario de usuario y contraseña, llamada a `POST /api/v1/auth/login`, almacenar JWT en memoria (no en localStorage), mostrar mensaje de error genérico en fallo, redirigir al dashboard tras éxito
    - Implementar guard de rutas protegidas: redirigir a `/login` si no hay sesión activa
    - Implementar cierre de sesión automático tras 30 minutos de inactividad
    - _Requisitos: 4.1, 4.2, 4.4_

  - [ ] 9.3 Implementar página de registros de fichaje con filtros y exportación
    - Crear `frontend/src/pages/Checkins.tsx`: tabla de registros con columnas `worker_name`, `event_type`, fecha y hora con zona horaria
    - Implementar filtros: selector de trabajador, rango de fechas (date picker), selector de tipo de evento
    - Implementar paginación conectada a `GET /api/v1/checkins`
    - Implementar botón de exportación CSV: llamar a `GET /api/v1/export/checkins.csv` con los filtros activos y descargar el archivo
    - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 9.4 Implementar página de gestión de trabajadores
    - Crear `frontend/src/pages/Workers.tsx`: tabla de trabajadores con estado activo/inactivo
    - Implementar formulario de alta de trabajador (nombre, `employee_id`, UID de token NFC inicial)
    - Implementar acción de desactivar trabajador con confirmación
    - Implementar formulario de asignación de nuevo token NFC a trabajador existente; mostrar mensaje de error 409 si el token ya está asignado
    - _Requisitos: 2.1, 2.2, 2.3, 2.5_

  - [ ] 9.5 Implementar página de auditoría
    - Crear `frontend/src/pages/Audit.tsx`: tabla del log de auditoría con columnas `admin_id`, `operation`, `entity_type`, `performed_at`
    - Implementar filtros por rango de fechas y administrador
    - _Requisitos: 6.2_

  - [ ]* 9.6 Escribir pruebas unitarias de componentes críticos del frontend
    - Pruebas con Vitest + React Testing Library para: formulario de login (éxito, error genérico), tabla de registros con filtros, formulario de alta de trabajador, manejo de error 409 en asignación de token
    - _Requisitos: 3.1, 3.2, 4.1, 4.2, 2.5_

- [ ] 10. Checkpoint — Verificar frontend completo
  - Asegurarse de que todas las pruebas del frontend pasan. Consultar al usuario si surgen dudas.

- [ ] 11. Integración y cableado final
  - [ ] 11.1 Conectar servicio NFC con backend en entorno de desarrollo
    - Configurar variables de entorno en `nfc_service/config.py`: URL del backend, `device_id`, `device_token`
    - Verificar flujo completo: detección NFC → `POST /api/v1/checkins` → respuesta con `event_type` → confirmación visual/sonora
    - _Requisitos: 1.1, 1.2, 1.3, 5.3_

  - [ ] 11.2 Escribir pruebas de integración del flujo de fichaje
    - Flujo completo: dispositivo → API → base de datos (token válido, token desconocido, trabajador desactivado)
    - Flujo offline: fichaje sin backend → almacenamiento local → sincronización posterior → verificar idempotencia
    - Flujo de autenticación: login → acceso a endpoint protegido → expiración de sesión → rechazo con 401
    - Exportación CSV con filtros combinados: verificar que el CSV coincide con la consulta
    - _Requisitos: 1.1, 1.4, 1.5, 4.1, 3.5_

  - [ ]* 11.3 Escribir pruebas de seguridad
    - Verificar que endpoints protegidos rechazan JWT inválidos/expirados/malformados (HTTP 401)
    - Verificar que mensajes de error de autenticación no revelan información sensible
    - Verificar que registros de fichaje no son modificables ni eliminables vía API
    - _Requisitos: 4.1, 4.2, 6.1_

- [ ] 12. Checkpoint final — Verificar sistema completo
  - Asegurarse de que todas las pruebas (unitarias, de propiedad e integración) pasan. Consultar al usuario si surgen dudas.

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Cada tarea referencia requisitos específicos para trazabilidad
- Los checkpoints garantizan validación incremental en cada capa
- Las pruebas de propiedad (Hypothesis) validan invariantes universales del sistema
- Las pruebas unitarias validan ejemplos concretos y casos límite
- El stack es: Python 3.11 + FastAPI (backend), Python 3 (servicio NFC), React 18 + TypeScript (frontend), PostgreSQL 15 (base de datos), SQLite (almacenamiento local NFC)

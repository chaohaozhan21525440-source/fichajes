# Documento de Requisitos

## Introducción

Este documento describe los requisitos para una aplicación de fichaje de trabajadores mediante tecnología NFC. El sistema permite a los empleados registrar su entrada y salida de la oficina acercando su tarjeta o dispositivo NFC a un lector situado en la entrada. Un administrador puede consultar los registros de fichaje de todos los trabajadores, incluyendo la hora exacta de cada evento.

## Glosario

- **Sistema**: La aplicación de fichaje de trabajadores en su conjunto.
- **Trabajador**: Empleado de la empresa que utiliza el dispositivo NFC para fichar.
- **Administrador**: Usuario con privilegios especiales que puede consultar todos los registros de fichaje.
- **Dispositivo_NFC**: Lector NFC físico situado en la entrada de la oficina que detecta las tarjetas o tokens NFC de los trabajadores.
- **Token_NFC**: Tarjeta, llavero u objeto NFC asignado a un trabajador concreto para identificarle.
- **Registro_de_Fichaje**: Entrada en la base de datos que contiene el identificador del trabajador, el tipo de evento (entrada o salida) y la marca de tiempo del momento en que se produjo.
- **Base_de_Datos**: Almacén persistente donde se guardan los registros de fichaje y la información de los trabajadores.
- **Panel_de_Administración**: Interfaz de usuario exclusiva para el Administrador donde se visualizan los registros de fichaje.

---

## Requisitos

### Requisito 1: Registro de fichaje mediante NFC

**Historia de usuario:** Como trabajador, quiero acercar mi Token_NFC al Dispositivo_NFC de la entrada para registrar mi fichaje, de modo que quede constancia automática de mi hora de entrada o salida sin necesidad de intervención manual.

#### Criterios de aceptación

1. WHEN el Dispositivo_NFC detecta un Token_NFC válido, THE Sistema SHALL crear un Registro_de_Fichaje con el identificador del Trabajador, el tipo de evento y la marca de tiempo UTC del momento de la detección.
2. WHEN el Dispositivo_NFC detecta un Token_NFC válido, THE Sistema SHALL persistir el Registro_de_Fichaje en la Base_de_Datos en un plazo máximo de 2 segundos desde la detección.
3. WHEN el Dispositivo_NFC detecta un Token_NFC válido, THE Sistema SHALL proporcionar una confirmación visual o sonora al Trabajador en un plazo máximo de 3 segundos desde la detección.
4. IF el Dispositivo_NFC detecta un Token_NFC no registrado en el sistema, THEN THE Sistema SHALL rechazar el fichaje y registrar un evento de intento fallido con la marca de tiempo y el identificador del token desconocido.
5. IF la Base_de_Datos no está disponible en el momento del fichaje, THEN THE Sistema SHALL almacenar el Registro_de_Fichaje localmente y sincronizarlo con la Base_de_Datos cuando la conexión se restablezca.

---

### Requisito 2: Gestión de trabajadores

**Historia de usuario:** Como administrador, quiero gestionar los trabajadores y sus Token_NFC asociados, de modo que solo los empleados activos puedan fichar en el sistema.

#### Criterios de aceptación

1. THE Administrador SHALL poder registrar un nuevo Trabajador proporcionando nombre completo, identificador único y el identificador del Token_NFC asignado.
2. THE Administrador SHALL poder asociar un Token_NFC a un Trabajador existente.
3. THE Administrador SHALL poder desactivar a un Trabajador, impidiendo que sus fichajes futuros sean aceptados por el Sistema.
4. WHEN el Administrador desactiva a un Trabajador, THE Sistema SHALL conservar todos los Registros_de_Fichaje históricos de dicho Trabajador en la Base_de_Datos.
5. IF el Administrador intenta registrar un Token_NFC ya asignado a otro Trabajador activo, THEN THE Sistema SHALL rechazar la operación y mostrar un mensaje de error indicando el conflicto.

---

### Requisito 3: Consulta de registros de fichaje

**Historia de usuario:** Como administrador, quiero consultar los registros de fichaje de todos los trabajadores, de modo que pueda supervisar la asistencia y los horarios del personal.

#### Criterios de aceptación

1. WHEN el Administrador accede al Panel_de_Administración, THE Sistema SHALL mostrar la lista de Registros_de_Fichaje ordenados por marca de tiempo descendente.
2. THE Administrador SHALL poder filtrar los Registros_de_Fichaje por Trabajador, por rango de fechas o por tipo de evento.
3. WHEN el Administrador aplica un filtro, THE Sistema SHALL devolver los resultados filtrados en un plazo máximo de 3 segundos.
4. THE Sistema SHALL mostrar en cada Registro_de_Fichaje el nombre del Trabajador, el tipo de evento, la fecha y la hora local con zona horaria.
5. THE Administrador SHALL poder exportar los Registros_de_Fichaje filtrados en formato CSV.

---

### Requisito 4: Autenticación y control de acceso

**Historia de usuario:** Como administrador, quiero que el Panel_de_Administración esté protegido por autenticación, de modo que solo yo pueda acceder a los datos de fichaje de los trabajadores.

#### Criterios de aceptación

1. WHEN un usuario intenta acceder al Panel_de_Administración, THE Sistema SHALL requerir credenciales válidas de Administrador antes de mostrar cualquier dato.
2. IF un usuario proporciona credenciales incorrectas, THEN THE Sistema SHALL denegar el acceso y mostrar un mensaje de error genérico sin revelar si el usuario o la contraseña son incorrectos.
3. IF un usuario falla la autenticación 5 veces consecutivas, THEN THE Sistema SHALL bloquear el acceso desde esa dirección IP durante 15 minutos.
4. WHILE una sesión de Administrador está activa, THE Sistema SHALL invalidar la sesión tras 30 minutos de inactividad y requerir nueva autenticación.
5. THE Sistema SHALL transmitir todas las comunicaciones entre el cliente y el servidor mediante HTTPS con TLS 1.2 o superior.

---

### Requisito 5: Determinación automática del tipo de evento

**Historia de usuario:** Como trabajador, quiero que el sistema determine automáticamente si estoy fichando una entrada o una salida, de modo que no tenga que indicarlo manualmente.

#### Criterios de aceptación

1. WHEN el Dispositivo_NFC detecta un Token_NFC válido y el último Registro_de_Fichaje del Trabajador es de tipo entrada, THE Sistema SHALL registrar el nuevo evento como salida.
2. WHEN el Dispositivo_NFC detecta un Token_NFC válido y el último Registro_de_Fichaje del Trabajador es de tipo salida o no existe ningún registro previo, THE Sistema SHALL registrar el nuevo evento como entrada.
3. THE Sistema SHALL mostrar al Trabajador el tipo de evento registrado (entrada o salida) en la confirmación visual o sonora del Dispositivo_NFC.

---

### Requisito 6: Auditoría e integridad de datos

**Historia de usuario:** Como administrador, quiero que los registros de fichaje sean inmutables y auditables, de modo que los datos no puedan ser alterados de forma no autorizada.

#### Criterios de aceptación

1. THE Base_de_Datos SHALL almacenar los Registros_de_Fichaje de forma que no puedan ser modificados ni eliminados una vez creados.
2. WHEN se produce cualquier operación de gestión de trabajadores por parte del Administrador, THE Sistema SHALL registrar en un log de auditoría el identificador del Administrador, la operación realizada y la marca de tiempo.
3. THE Sistema SHALL realizar copias de seguridad de la Base_de_Datos con una frecuencia mínima de una vez cada 24 horas.

# GRH 0652 · Aula SCORM · evaluación criterial

Implementación completa del módulo **0652 · Gestión de Recursos Humanos** organizada en cuatro RA/UT.

## 0. Preparar un servidor Ubuntu/Debian completamente limpio

Si el servidor acaba de instalarse y no dispone todavía de herramientas básicas, ejecuta primero estos pasos desde una consola SSH.

> Si has iniciado sesión directamente como `root`, puedes quitar `sudo` de los comandos.

### 0.1. Actualizar el sistema

```bash
sudo apt update
sudo apt -y full-upgrade
```

Si durante la actualización se instala un kernel nuevo o el sistema indica que es necesario reiniciar:

```bash
sudo reboot
```

Después del reinicio, vuelve a conectarte por SSH y continúa con el siguiente paso.

### 0.2. Instalar Git, curl y utilidades básicas

```bash
sudo apt update
sudo apt -y install git curl ca-certificates unzip
```

Estas herramientas se utilizan para descargar el instalador, clonar o actualizar el repositorio y trabajar con los paquetes de despliegue.

Comprueba que Git y curl han quedado instalados:

```bash
git --version
curl --version
```

### 0.3. Opción recomendada: clonar el repositorio

Si quieres conservar una copia local del proyecto en el servidor:

```bash
cd /opt
sudo git clone https://github.com/atreyu1968/CFGSAF.git
sudo chown -R "$USER":"$USER" /opt/CFGSAF
cd /opt/CFGSAF/grh0652
```

Para actualizar posteriormente esa copia con los últimos cambios publicados en GitHub:

```bash
cd /opt/CFGSAF
git pull --ff-only
```

Si solo quieres ejecutar el instalador automático, no es obligatorio clonar antes el repositorio; basta con tener `curl` instalado y usar el comando de la siguiente sección.

---

## Credenciales de administración y primer arranque

La aplicación utiliza ahora **cuentas de administrador con usuario y contraseña**. En una instalación nueva, el instalador comprueba el backend después de arrancarlo y, si no existe ningún administrador activo, abre obligatoriamente el asistente de creación de credenciales.

También se aplica la misma regla durante una **actualización**: si la base de datos existente no contiene ningún administrador activo, `grh0652-update` detiene el proceso normal y solicita la creación de uno antes de dar la actualización por terminada.

El asistente solicita:

- usuario administrador;
- nombre visible;
- correo electrónico opcional;
- contraseña y confirmación.

La contraseña debe tener al menos 12 caracteres y combinar al menos tres grupos entre mayúsculas, minúsculas, números y símbolos. **La contraseña no se guarda en archivos de texto del servidor.**

Panel de administración:

```text
https://TU_DOMINIO/admin.html
```

Desde este panel se puede consultar el estado global, gestionar administradores, crear accesos de alumnado, revisar información técnica, descargar copias de seguridad y abrir el panel docente.

Para instalaciones totalmente desatendidas se pueden suministrar las credenciales por argumentos:

```bash
--admin-user admin \
--admin-password 'UnaClaveLargaYSegura123!' \
--admin-name 'Administrador GRH0652' \
--admin-email admin@centro.es
```

Si la actualización se ejecuta sin terminal interactivo y no existe administrador, el proceso se detendrá con un mensaje claro en lugar de dejar la aplicación sin acceso administrativo.

## Instalación automática en Ubuntu

La forma recomendada de desplegar GRH0652 en producción es mediante el instalador incluido en el repositorio:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | sudo bash
```

El instalador configura automáticamente Docker Engine, Docker Compose, FastAPI, SQLite, Nginx, bancos privados, API same-origin, Cloudflare Tunnel opcional, backups diarios y comandos de mantenimiento.

Para una instalación no interactiva con un túnel Cloudflare ya existente:

```bash
curl -fsSL https://raw.githubusercontent.com/atreyu1968/CFGSAF/main/grh0652/install-ubuntu.sh | \
sudo bash -s -- \
  --domain grh.midominio.es \
  --private-banks /root/GRH0652_PRIVATE_BANKS_v1.zip \
  --cloudflare-mode existing \
  --non-interactive
```

El origen local que debe publicar Cloudflare es:

```text
http://localhost:8080
```

Los bancos privados deben permanecer fuera de Git y nunca deben ubicarse en el directorio web público.

Documentación detallada: [INSTALL_UBUNTU.md](INSTALL_UBUNTU.md).

## Registros disponibles desde la aplicación

Se ha revisado el modelo de datos para que las entidades que requieren alta manual dispongan de una vía de registro desde la interfaz, no solamente desde la API o desde SQLite.

| Registro | Alta | Edición / mantenimiento | Ubicación |
|---|---|---|---|
| Administradores | Sí | contraseña, estado, nuevas cuentas | `admin.html` |
| Grupos | Sí | nombre, curso, descripción, estado, miembros | `admin.html` |
| Alumnado | Sí, individual y masiva | datos, grupos, estado, regeneración de clave | `admin.html` |
| Matrícula alumno-grupo | Sí | añadir y retirar alumnado | `admin.html` |
| Preguntas de examen | Sí | alta, edición, borrado e importación JSON | `banks.html` |
| Actividades de recuperación | Sí | alta, edición, borrado e importación JSON | `banks.html` |
| Claves privadas de Portafolio | Sí | alta, edición, borrado e importación JSON | `banks.html` |
| Rúbricas de IA | Sí | alta, edición y borrado | `teacher.html` |
| Configuración de evaluación | Sí | edición por RA | `teacher.html` |
| Rectificaciones de calificación | Sí | registro motivado y reversión | `teacher.html` |

Los intentos, evidencias, resultados, planes de recuperación, versiones de examen y auditorías **no se dan de alta manualmente**, porque son registros transaccionales que genera automáticamente la aplicación como consecuencia del trabajo del alumnado o de una actuación docente. Esto evita crear resultados artificiales sin trazabilidad.

Al regenerar la clave de un alumno se conserva su ficha, grupos, progreso y resultados. Desactivar un alumno impide su acceso sin borrar su historial.

## Integración con CAMPUS mediante LTI 1.3

GRH0652 puede funcionar como **herramienta LTI 1.3 / LTI Advantage** para Moodle/CAMPUS. En este modo el alumnado entra desde el aula virtual y no necesita volver a autenticarse con la contraseña temporal `1234`.

La integración incluye:

- OIDC Login de LTI 1.3.
- Validación de `id_token` mediante el JWKS de CAMPUS.
- Clave RSA propia persistente y publicación de JWKS.
- Deep Linking para seleccionar UT1, UT2, UT3 o UT4 desde el aula.
- Assignment and Grade Services (AGS) para devolver a CAMPUS la nota final del RA cuando la plataforma concede el scope correspondiente.
- Names and Role Provisioning Services (NRPS) para sincronizar el alumnado de un aula cuando CAMPUS concede ese servicio.
- Creación automática de un grupo local para cada contexto/aula LTI.
- Identificación por `sub` LTI de forma predeterminada. Existe un modo opcional CIAL si CAMPUS lo proporciona mediante un custom claim llamado `cial`; GRH0652 utiliza una huella criptográfica para la correspondencia y no necesita mostrar el CIAL en la interfaz.

### 1. Datos de GRH0652 que deben registrarse en CAMPUS

Después de instalar o actualizar el servidor, entra como administrador en:

```text
https://TU_DOMINIO/lti-admin.html
```

La pantalla muestra automáticamente:

```text
OIDC Initiation URL: https://TU_DOMINIO/api/lti/login
Target / Tool URL:   https://TU_DOMINIO/api/lti/launch
Redirect URI:        https://TU_DOMINIO/api/lti/launch
JWKS URL:            https://TU_DOMINIO/api/lti/jwks
```

También puede consultarse en formato JSON:

```text
https://TU_DOMINIO/api/lti/configuration
```

La clave privada RSA se genera automáticamente en el volumen persistente de datos y **nunca se publica**. CAMPUS solo necesita la URL JWKS.

### 2. Datos que CAMPUS debe facilitar a GRH0652

Una vez registrada la herramienta en Moodle/CAMPUS, introduce en `lti-admin.html`:

- Issuer (`iss`).
- Client ID.
- Deployment ID, si ya está disponible.
- Authentication request / OIDC login URL.
- OAuth2 access token URL.
- Public keyset / JWKS URL de CAMPUS.

Si el Deployment ID todavía no se conoce, puede dejarse vacío inicialmente y completarse después.

### 3. Vincular específicamente UT1 a un aula

La opción recomendada es **Deep Linking**. Al añadir GRH0652 como herramienta externa en el aula, el selector devuelve cuatro recursos:

- UT1 · Gestión de la contratación laboral.
- UT2 · Modificación, suspensión y extinción.
- UT3 · Seguridad Social.
- UT4 · Retribución, nóminas, cotización e IRPF.

Selecciona **UT1**. GRH0652 devuelve a CAMPUS un `ltiResourceLink` con:

```text
grh_course_id=GRH0652_UT1
```

y solicita un elemento de calificación de 100 puntos para que AGS pueda devolver la nota.

Si se configura la actividad manualmente sin Deep Linking, debe enviarse como parámetro personalizado:

```text
grh_course_id=GRH0652_UT1
```

Si no se recibe ningún parámetro, GRH0652 utiliza UT1 como valor predeterminado.

### 4. Identidad, grupos y matrícula

En el primer lanzamiento de un alumno desde CAMPUS:

1. se valida la firma LTI;
2. se crea una identidad local pseudónima basada en el `sub` de LTI;
3. se crea o actualiza el grupo local correspondiente al contexto del aula;
4. el alumno queda asignado al grupo;
5. se crea una sesión LTI temporal de GRH0652.

Si CAMPUS concede NRPS, desde **Administración → LTI 1.3 · CAMPUS** aparece el aula detectada y el botón **Sincronizar alumnado**. La sincronización incorpora al grupo local las personas con rol Learner.

### 5. Calificaciones

Si CAMPUS concede AGS y proporciona un `lineitem`, GRH0652 envía automáticamente la nota final del RA sobre 100. Si el recurso no trae un `lineitem` pero la plataforma permite crearlo, GRH0652 intenta crear uno.

Los envíos se auditan en la tabla `lti_grade_log` y no se repite un envío cuando la nota no ha cambiado.

### 6. Acceso alternativo

La integración LTI no elimina el acceso independiente. Los dos sistemas pueden coexistir:

- CAMPUS → LTI 1.3 → acceso sin contraseña adicional.
- Acceso directo → usuario del alumno + contraseña temporal `1234`, con cambio obligatorio en el primer acceso.
- Código legado → se conserva para compatibilidad con cuentas creadas por versiones anteriores.

> El registro de una herramienta LTI 1.3 suele requerir permisos de administración o la intervención de quien administre las herramientas externas en la plataforma Moodle/CAMPUS. GRH0652 deja preparada toda la parte correspondiente a la herramienta.

## Flujo del alumnado
1. Teoría e infografías.
2. Práctica guiada no evaluable: 3 intentos por ejercicio; al agotarlos se muestra orientación/solución.
3. Portafolio de Actividades: evaluable, máximo 2 intentos por actividad.
4. Examen evaluable: 1 intento, solo disponible cuando lo activa el profesor.
5. Cálculo por criterios y RA.
6. Programa de recuperación automático con los CE no superados.

## Reglas configurables
El panel `teacher.html` permite configurar pesos Portafolio/Examen dentro de cada RA, nota mínima del RA, porcentaje mínimo de CE superados, nota mínima por CE, número de preguntas por CE, duración y activación del examen.

La ponderación **entre RA para obtener una nota global de módulo está desactivada** hasta incorporar una fuente documental que la acredite. El dashboard no muestra porcentajes RA no verificados.

## Identificación y persistencia
El alumnado accede mediante un código/token personal. `index.html` valida ese token contra `/api/student/session` y obtiene del servidor el `student_id`; el identificador no se acepta desde la URL. Las operaciones autoritativas vuelven a comprobar que el token pertenece al alumno declarado.

Para evaluación real multiusuario debe ejecutarse `server/app.py` detrás de HTTPS. El backend guarda estado, evidencias, intentos, respuestas, resultados, revisiones y recuperación. El alumno puede reanudar desde otro dispositivo utilizando su mismo código personal.

## Anticopia y examen seguro
El examen se genera por alumno en el servidor, con orden de preguntas y respuestas alterado y una versión exacta persistida por intento. Puede aplicar pantalla completa, registro de pérdida de foco y política configurable de incidencias.

## Bancos privados
Las respuestas de examen, recuperación y Portafolio no se versionan. `docker-compose.yml` monta `grh0652/private-banks/` en modo solo lectura. El backend valida los bancos privados al arrancar y vincula las claves de Portafolio a la versión pública mediante `public_hash`.

## Estructura
- `index.html`: acceso del alumnado.
- `course.html`: dashboard de los cuatro RA.
- `player.html`: reproductor SCORM 1.2.
- `admin.html`: panel de administración, administradores, grupos y alumnado.
- `banks.html`: registro y mantenimiento de bancos de examen, recuperación y Portafolio.
- `teacher.html`: panel docente.
- `assets/scorm-api.js`: API SCORM 1.2.
- `assets/evidence-store.js`: adaptador de persistencia.
- `assets/secure-exam.js`: examen seguro compartido.
- `scorm/ut1/`–`scorm/ut4/`: SCO pedagógicos.
- `server/`: API FastAPI + SQLite.
- `private-banks/`: punto de montaje local para claves no versionadas.

## Arquitectura multi-RA
El módulo se organiza en:
- RA1 / UT1: Gestión de la contratación laboral.
- RA2 / UT2: Modificación, suspensión y extinción del contrato.
- RA3 / UT3: Obligaciones empresariales con la Seguridad Social.
- RA4 / UT4: Retribución, nóminas, cotización e IRPF.

Los cuatro RA están activos en la aplicación principal y cada uno utiliza su propio `course_id`, sus CE, teoría, práctica y evaluación.

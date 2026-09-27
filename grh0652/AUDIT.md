# Auditoría GRH0652

## Estado funcional automatizado
- Límites autoritativos: práctica 3, Portafolio 2, examen 1.
- Reanudación del mismo intento de examen.
- Examen desactivado por defecto.
- Validación de ponderaciones internas Portafolio/Examen al 100 % y versionado de configuración.
- Cierre de evaluación y recuperación solo para alumnado no superado.
- CI ejecuta pytest en cambios bajo `grh0652/`. La suite actual contiene **130 pruebas** y el criterio de cierre exige `success` sobre el mismo HEAD que se pretenda desplegar.
- Ayuda contextual por botón derecho validada en todos los campos de nómina y contratos.
- Los bancos privados del Portafolio quedan vinculados mediante `public_hash` a la versión del banco público; si cambia una actividad, el backend bloquea la corrección hasta reprovisionar sus claves.
- Las ponderaciones globales de RA no verificadas están desactivadas en el dashboard y no se presentan como oficiales.

## Hallazgos resueltos

### 1. Contenido heredado de RA1 en RA2 y RA3 — RESUELTO
- UT2 muestra exclusivamente CE 2.a–2.f y 36 actividades.
- UT3 muestra exclusivamente CE 3.a–3.h y 48 actividades.
- Se eliminaron pantallas `pract-1*`, textos de contratación heredados y fuentes genéricas de RA1.
- Existe una prueba de regresión que impide volver a introducir pantallas prácticas de otro RA.

### 2. Carga privada de bancos — RESUELTO A NIVEL DE MECANISMO
- `docker-compose.yml` monta `./private-banks` como `/private-banks:ro`.
- `GRH_PRIVATE_BANK_DIR` activa la carga al arrancar el backend.
- Se admiten bancos privados de `exam`, `recovery` y `portfolio`.
- Examen y recuperación se validan antes de registrarse.
- El Portafolio privado debe cubrir exactamente el banco público de la unidad y coincidir en `id`, CE y tipo.
- Cada clave de Portafolio guarda `public_hash`; el arranque reprovisiona la clave cuando el JSON privado corresponde a la versión pública actual.
- CI comprueba carga, idempotencia, rechazo de bancos inválidos, refresco de hash y disponibilidad posterior.
- Los JSON con respuestas están excluidos de Git y deben provisionarse en el servidor antes del despliegue real.

### 3. Identidad del alumnado — RESUELTO
- El acceso del alumno se realiza mediante código/token personal validado en `/api/student/session`.
- El `student_id` se obtiene del servidor a partir del token; ya no se toma de parámetros `student` en la URL.
- `require_student()` compara la identidad declarada con la asociada al token y devuelve 403 ante intento de suplantación.
- Se eliminó el parámetro `?student=` residual del reproductor.
- CI intenta expresamente usar el token de un alumno declarando el identificador de otro y exige el rechazo.

### 4. Ponderaciones globales RA no acreditadas — RIESGO NEUTRALIZADO
- Los antiguos valores 25/20/15/40 no estaban respaldados en el repositorio por la programación oficial.
- Se han retirado de `course-config.js` y sustituido por `weight:null`.
- El dashboard muestra “Ponderación del RA: pendiente de validar con la programación oficial”.
- No se calculará ni comunicará una ponderación global de módulo hasta disponer de una fuente documental válida.

## Hallazgo editorial resuelto

### Variedad de bancos públicos RA2–RA4 — RESUELTO
- Todos los CE de RA2, RA3 y RA4 mantienen al menos seis actividades evaluables.
- Los enunciados genéricos repetitivos han sido sustituidos por situaciones profesionales contextualizadas.
- Cada CE de RA2–RA4 exige al menos una producción propia del alumnado mediante respuesta libre, texto, caso o cálculo.
- Los CE con componente numérico relevante incorporan actividades de cálculo explícitas: 2.b; 3.b–3.c; 4.a–4.f.
- Se mantienen actividades de selección, V/F, multirrespuesta, ordenación, casos y cálculos para combinar evaluación objetiva y aplicación profesional. El motor conserva soporte de emparejamiento, pero RA1 ya no publica pares evaluables que revelen la asociación correcta.
- CI bloquea regresiones mediante pruebas de diversidad, ausencia de duplicados, presencia de actividades semánticas y cobertura de cálculos.
- Las claves privadas permanecen protegidas por `public_hash`, por lo que cualquier cambio posterior en una actividad pública obliga a reprovisionar su respuesta privada antes de corregirla.

## Seguridad de bancos evaluables — RESUELTO EN CÓDIGO

- RA1 fue rotado completamente: 54 actividades nuevas, identificadores nuevos y eliminación de `match` evaluable público. Las versiones históricas que llegaron a contener claves ya no corresponden al banco actual.
- RA2–RA4 ya habían sido reescritos después de retirar las claves; además se han rotado las posiciones públicas de `choice`, `multi` y `order`.
- Los cambios de opciones modifican `public_hash`, por lo que el backend rechaza cualquier clave privada anterior.
- `calculation` se corrige numéricamente de forma determinista, aceptando representaciones equivalentes como `94`, `94.0` o `94,00`.
- Existe `validate_private_banks.py`, que exige los 12 bancos privados, coincidencia exacta del Portfolio, al menos 3 preguntas de examen por CE y al menos 2 actividades de recuperación por CE.
- El `readiness` del backend y el preflight docente exigen también un mínimo de **2 actividades de recuperación por CE**, de modo que servidor y validador local aplican el mismo criterio.
- Existe `production_acceptance.py`, que ejecuta una aceptación remota **no destructiva** de producción: salud, readiness UT1–UT4, configuración, monitor, Additio y backup con validación de integridad.
- Las claves reales continúan fuera de Git y deben copiarse únicamente al servidor de producción.

## Pendiente documental no bloqueante para evaluación por RA
Para obtener una **calificación global ponderada del módulo**, debe incorporarse al repositorio o documentarse externamente la programación oficial que establezca la ponderación entre RA. Mientras no exista esa fuente, el sistema mantiene esa ponderación desactivada.

## Criterio de cierre
La base de código cumple ya el criterio técnico de CI para candidata a v1.0. Antes de etiquetar la versión estable deben completarse en el despliegue real los siguientes controles operativos:
- copiar al servidor los bancos privados definitivos de examen, recuperación y Portafolio y ejecutar `python validate_private_banks.py ../private-banks`;
- verificar `/api/teacher/readiness/{course_id}` con `ready:true` en GRH0652_UT1, GRH0652_UT2, GRH0652_UT3 y GRH0652_UT4;
- conservar el artefacto `GRH0652 release candidate` generado automáticamente desde el HEAD de cierre, que incluye los cuatro SCORM 1.2, el bundle de aplicación, `RELEASE_INFO.txt` y `SHA256SUMS.txt`;
- ejecutar `production_acceptance.py` contra el servidor real y conservar su resultado en verde;
- realizar después la prueba funcional docente/alumno, incluyendo examen seguro, recuperación y una restauración controlada de backup, ya que esas acciones sí modifican estado.

## Validación CI y release
- Workflow `GRH0652 tests`: debe figurar como **success** sobre el HEAD final; la suite actual contiene **130 pruebas**.
- Workflow `GRH0652 release candidate`: se ejecuta automáticamente en cada push a `main`, además de poder ejecutarse manualmente o mediante una etiqueta `grh0652-v*`.
- El artefacto de release registra el SHA exacto en `RELEASE_INFO.txt`, genera los cuatro SCORM y el bundle desplegable y publica `SHA256SUMS.txt` para verificar integridad.
- La condición para etiquetar v1.0 exige que **tests y release candidate** correspondan al mismo HEAD final y terminen en **success**.

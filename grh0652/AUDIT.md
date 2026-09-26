# Auditoría GRH0652

## Estado funcional automatizado
- Límites autoritativos: práctica 3, Portafolio 2, examen 1.
- Reanudación del mismo intento de examen.
- Examen desactivado por defecto.
- Validación de ponderaciones internas Portafolio/Examen al 100 % y versionado de configuración.
- Cierre de evaluación y recuperación solo para alumnado no superado.
- CI ejecuta pytest en cambios bajo `grh0652/`.
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

## Hallazgo pendiente

### Variedad de bancos públicos RA2–RA4
Aunque existen al menos seis actividades por CE, sin duplicados literales y con varios tipos de interacción, parte de los bancos públicos de servidor conserva patrones demasiado repetitivos. Deben evolucionar hacia más:
- supuestos profesionales contextualizados;
- cálculos y análisis numéricos cuando el CE lo permita;
- clasificación y selección razonada;
- ordenación de procedimientos;
- detección y corrección de errores;
- cumplimentación y verificación documental.

La protección `public_hash` y el nuevo aprovisionamiento privado de Portafolio permiten realizar esta renovación sin aceptar silenciosamente claves de una versión anterior.

## Pendiente documental no bloqueante para evaluación por RA
Para obtener una **calificación global ponderada del módulo**, debe incorporarse al repositorio o documentarse externamente la programación oficial que establezca la ponderación entre RA. Mientras no exista esa fuente, el sistema mantiene esa ponderación desactivada.

## Criterio de cierre
No marcar como cerrado editorialmente el banco evaluativo hasta resolver la variedad de RA2–RA4, provisionar los bancos privados reales del despliegue y superar `GRH0652 tests` sobre el HEAD definitivo.

## Validación CI
La condición de cierre exige que el workflow `GRH0652 tests` figure como **success** sobre el HEAD definitivo. No se considera suficiente un rerun de un SHA anterior.

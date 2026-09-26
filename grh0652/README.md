# GRH 0652 · Aula SCORM · evaluación criterial

Implementación completa del módulo **0652 · Gestión de Recursos Humanos** organizada en cuatro RA/UT.

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

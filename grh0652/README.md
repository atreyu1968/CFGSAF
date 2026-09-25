# GRH 0652 · Aula SCORM · evaluación criterial

Implementación de la UT1 / RA1 de Gestión de Recursos Humanos.

## Flujo del alumnado
1. Teoría e infografías.
2. Práctica guiada no evaluable: 3 intentos por ejercicio; al agotarlos se muestra orientación/solución.
3. Portafolio de Actividades: evaluable, máximo 2 intentos por actividad.
4. Examen tipo test: evaluable, 1 intento, solo disponible cuando lo activa el profesor.
5. Cálculo por criterios y RA.
6. Programa de recuperación automático con los CE no superados.

## Reglas configurables
El panel `teacher.html` permite configurar pesos Portafolio/Examen, nota mínima del RA, porcentaje mínimo de CE superados (80 % por defecto), nota mínima por CE, número de preguntas por CE, duración y activación del examen.

## Anticopia
El examen se genera por alumno con orden de preguntas y respuestas alterado, conservando el CE evaluado y la trazabilidad de la versión recibida.

## Persistencia
Sin servidor, el SCORM conserva una copia local. Para evaluación real multiusuario debe ejecutarse `server/app.py` detrás de HTTPS y configurar su URL. El backend guarda estado, evidencias, intentos, respuestas, resultados y recuperación por alumno. El alumno puede reanudar desde otro dispositivo cuando usa el mismo identificador y el servidor está configurado.

## Estructura
- `index.html`: acceso del alumnado.
- `player.html`: reproductor SCORM 1.2.
- `teacher.html`: panel docente.
- `assets/scorm-api.js`: API SCORM 1.2.
- `assets/evidence-store.js`: adaptador de persistencia.
- `scorm/ut1/`: SCO real.
- `server/`: API FastAPI + SQLite.

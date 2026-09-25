# GRH 0652 · Reproductor SCORM en GitHub Pages

Esta carpeta contiene una **versión específica para GitHub Pages del SCORM 1.2 real de la UT1**, acompañada por un reproductor que expone la API que espera un SCO SCORM 1.2.

## Arquitectura

- `index.html`: portal para el alumnado.
- `player.html`: reproductor que crea la API SCORM 1.2 y carga el SCO en un iframe.
- `assets/scorm-api.js`: implementación local de la API SCORM 1.2.
- `scorm/ut1/imsmanifest.xml`: manifiesto SCORM.
- `scorm/ut1/index.html`: SCO de la UT1.
- `scorm/ut1/assets/style.css`: estilos.
- `scorm/ut1/assets/scorm.js`: navegación, 54 actividades, examen de 36 preguntas y seguimiento.
- `scorm/ut1/assets/infografias/`: recursos visuales de la unidad.
- `scorm/ut1/assets/media/`: esquemas de apoyo.

## Seguimiento

GitHub Pages es estático. El reproductor guarda en `localStorage`, separado por alumno y curso:

- cmi.core.lesson_location
- cmi.suspend_data
- cmi.core.lesson_status
- cmi.core.score.raw
- interacciones registradas por el SCO

Este seguimiento permite reanudar en el mismo navegador, pero **no es un registro centralizado ni una calificación oficial**. Para ello debe utilizarse el ZIP SCORM en Moodle u otro LMS.

## Autor

Francisco Javier González Rolo

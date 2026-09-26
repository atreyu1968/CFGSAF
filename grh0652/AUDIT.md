# Auditoría GRH0652

## Estado funcional automatizado
- Límites autoritativos: práctica 3, Portafolio 2, examen 1.
- Reanudación del mismo intento de examen.
- Examen desactivado por defecto.
- Validación de ponderaciones 100 % y versionado de configuración.
- Cierre de evaluación y recuperación solo para alumnado no superado.
- CI ejecuta pytest en cambios bajo grh0652/.

## Hallazgos de contenido pendientes
1. RA2, RA3 y RA4 conservan fragmentos HTML/teoría heredados de UT1, incluidos textos de contratación e identificadores visuales pract-1*. No deben considerarse cerrados editorialmente.
2. Los bancos RA2–RA4 son todavía demasiado repetitivos; deben sustituirse por supuestos, cálculos, clasificación, ordenación, detección de errores y cumplimentación documental reales.
3. Las ponderaciones globales RA 25/20/15/40 de course-config.js no están acreditadas en el repositorio como procedentes de la programación oficial. No deben usarse para una calificación final de módulo hasta verificarlas.
4. Los bancos de examen y recuperación deben cargarse al backend durante el despliegue; la existencia de constantes en el SCO no los registra automáticamente en exam_banks/recovery_banks.
5. Falta autenticación fuerte del alumno: el identificador por query/localStorage sigue siendo suplantable. La persistencia es central, pero la identidad todavía no es segura.

## Criterio de cierre
No marcar el proyecto como producción hasta resolver 1–5 y superar CI.

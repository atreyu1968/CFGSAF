# Auditoría GRH0652

## Estado funcional automatizado
- Límites autoritativos: práctica 3, Portafolio 2, examen 1.
- Reanudación del mismo intento de examen.
- Examen desactivado por defecto.
- Validación de ponderaciones 100 % y versionado de configuración.
- Cierre de evaluación y recuperación solo para alumnado no superado.
- CI ejecuta pytest en cambios bajo `grh0652/`.
- Ayuda contextual por botón derecho validada en todos los campos de nómina y contratos.
- Los bancos privados del Portafolio quedan vinculados mediante `public_hash` a la versión del banco público; si cambia una actividad, el backend bloquea la corrección hasta reprovisionar sus claves.

## Hallazgos resueltos

### 1. Contenido heredado de RA1 en RA2 y RA3 — RESUELTO
- UT2 muestra exclusivamente CE 2.a–2.f y 36 actividades.
- UT3 muestra exclusivamente CE 3.a–3.h y 48 actividades.
- Se eliminaron pantallas `pract-1*`, textos de contratación heredados y fuentes genéricas de RA1.
- Existe una prueba de regresión que impide volver a introducir pantallas prácticas de otro RA.

### 4. Carga de bancos de examen y recuperación — MECANISMO RESUELTO
- `docker-compose.yml` monta `./private-banks` como `/private-banks:ro`.
- `GRH_PRIVATE_BANK_DIR` activa la carga de bancos privados al arrancar el backend.
- El backend valida estructura, curso, CE, identificadores y respuestas antes de registrar examen/recuperación.
- CI verifica carga, idempotencia, rechazo de bancos inválidos y disponibilidad posterior en `readiness`.
- Los JSON con respuestas no se versionan: deben provisionarse en `grh0652/private-banks/` en cada despliegue real.

## Hallazgos pendientes

1. **Variedad de bancos públicos RA2–RA4.** Aunque ya existen al menos seis actividades por CE y no hay duplicados literales, varios bancos de servidor conservan patrones demasiado repetitivos. Deben evolucionar hacia más supuestos, cálculos, clasificación, ordenación, detección de errores y cumplimentación documental. La protección `public_hash` ya permite hacerlo sin riesgo de usar claves privadas obsoletas.

2. **Ponderaciones globales RA.** Las ponderaciones 25/20/15/40 de `course-config.js` no están acreditadas en el repositorio como procedentes de la programación oficial. No deben utilizarse como calificación final de módulo hasta verificarlas documentalmente.

3. **Identidad del alumnado.** La persistencia es central y cada alumno dispone de token, pero el flujo de acceso todavía debe auditarse para garantizar que el identificador inicial no pueda suplantarse desde query/localStorage.

## Criterio de cierre
No marcar el proyecto como producción hasta resolver los tres hallazgos pendientes y superar CI sobre el HEAD definitivo.

## Validación CI actual
- HEAD validado: `e5bf951bf11d4771861dbeec648d69e44efa2cb7`.
- Workflow: `GRH0652 tests`.
- Resultado: **success**.
- La condición de cierre exige repetir esta validación sobre el HEAD definitivo después de cualquier cambio posterior.

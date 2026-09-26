# Servidor de evidencias GRH0652

Backend FastAPI + SQLite para identificación por token, reanudación, evidencias, configuración docente, Portafolio, examen, recuperación, revisión con IA y resultados.

## Puesta en marcha
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export GRH_TEACHER_TOKEN='una-clave-segura'
export GRH_ALLOWED_ORIGINS='https://su-aula.example'
uvicorn app:app --host 0.0.0.0 --port 8080
```

Publique el servicio detrás de HTTPS. En el aula web configure la URL con `?api=https://su-servidor` una vez; el reproductor la conservará en el navegador.

## Seguridad e identidad
El servidor no arranca sin `GRH_TEACHER_TOKEN`. Cada alumno dispone de un token personal generado por el profesor. `/api/student/session` deriva la identidad desde ese token y `require_student()` rechaza cualquier petición en la que el `student_id` declarado no coincida con su token.

Configure `GRH_ALLOWED_ORIGINS` con los orígenes HTTPS autorizados. SQLite trabaja en WAL.

## Evaluación autoritativa
Los límites de intentos se registran en servidor: práctica máximo 3, Portafolio máximo 2, examen máximo 1 y recuperación máximo 1. Refrescar o reconectar recupera el intento iniciado y no concede uno nuevo.

El panel docente puede cerrar la evaluación. Al cerrarla se congela la configuración y se crean planes de recuperación para los CE pendientes.

## Bancos privados
Las respuestas correctas no deben almacenarse en archivos públicos. Puede provisionarlas mediante los endpoints docentes o mediante `GRH_PRIVATE_BANK_DIR`.

Con Docker Compose, `../private-banks` se monta como `/private-banks:ro`. El arranque admite:
- `kind: "exam"`;
- `kind: "recovery"`;
- `kind: "portfolio"`.

El Portafolio privado debe cubrir exactamente la versión pública correspondiente. Cada clave queda asociada a un `public_hash`; si el contenido público cambia, una clave antigua no puede corregir silenciosamente la nueva actividad.

## Exámenes generados en servidor
Al iniciar una convocatoria, el servidor selecciona el número configurado de preguntas por CE, aleatoriza preguntas y opciones y persiste una versión exacta por intento. La respuesta correcta no se incluye en el payload enviado al alumno. La misma versión se recupera tras una reconexión.

## Comprobación previa
El endpoint docente de `readiness` permite comprobar que existen bancos suficientes y configuración válida antes de habilitar una evaluación real.

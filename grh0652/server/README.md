# Servidor de evidencias GRH0652

Backend mínimo FastAPI + SQLite para identificación, reanudación, evidencias, configuración docente, examen y resultados.

## Puesta en marcha
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export GRH_TEACHER_TOKEN='una-clave-segura'
uvicorn app:app --host 0.0.0.0 --port 8080
```

Publique el servicio detrás de HTTPS. En el aula web configure la URL con `?api=https://su-servidor` una vez; el reproductor la conservará en el navegador.


## Seguridad y evaluación autoritativa
El servidor ya no arranca sin `GRH_TEACHER_TOKEN`. Configure también `GRH_ALLOWED_ORIGINS` con los orígenes HTTPS autorizados, separados por comas. SQLite trabaja en WAL.

Los intentos críticos se registran en servidor: práctica máximo 3, Portafolio máximo 2, examen máximo 1 y recuperación máximo 1. El examen debe iniciarse contra `/api/attempts/start`; refrescar o reconectar recupera el intento iniciado y no concede uno nuevo. El panel docente puede cerrar cada evaluación; al cerrarla se congela la configuración y se crean planes de recuperación para los CE pendientes de cada alumno.

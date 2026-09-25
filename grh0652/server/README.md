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

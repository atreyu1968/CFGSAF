# Bancos privados de evaluación GRH0652

Este directorio se monta en el servidor como `/private-banks` en modo solo lectura. Los JSON reales contienen respuestas y **no deben versionarse**. El `.gitignore` del repositorio excluye `grh0652/private-banks/*.json`.

Cree localmente archivos `*.json` con uno de estos esquemas.

## Examen
```json
{"course_id":"GRH0652_UT1","kind":"exam","questions":[{"id":"e1","ce":"1.a","q":"Enunciado","options":["A","B"],"answer":0,"type":"choice"}]}
```

## Recuperación
```json
{"course_id":"GRH0652_UT1","kind":"recovery","items":[{"id":"r1","ce":"1.a","kind":"choice","prompt":"Enunciado","options":["A","B"],"answer":1,"feedback":"Orientación tras responder"}]}
```

La recuperación admite `choice`, `tf`, `multi`, `free`, `text`, `case`, `calculation`, `order` y `match`. En `order`, `options` contiene los elementos y `answer` la secuencia de índices correcta. En `match`, los pares visibles se declaran en `pairs` y la clave privada conserva en `answer` la correspondencia por índices:

```json
{"course_id":"GRH0652_UT1","kind":"recovery","items":[
  {"id":"r-order","ce":"1.b","kind":"order","prompt":"Ordena el procedimiento","options":["Paso A","Paso B","Paso C"],"answer":[0,1,2]},
  {"id":"r-match","ce":"1.c","kind":"match","prompt":"Relaciona organismo y función","options":[],"pairs":[["TGSS","Afiliación, altas y bajas"],["SEPE","Comunicación de contratos"]],"answer":[0,1]}
]}
```

## Portafolio
El archivo privado de Portafolio solo necesita metadatos y respuesta. Debe contener **exactamente** los mismos `id`, CE y tipos que el banco público de la unidad.

```json
{"course_id":"GRH0652_UT2","kind":"portfolio","items":[
  {"id":"2.ap1","ce":"2.a","kind":"choice","answer":0},
  {"id":"2.ap2","ce":"2.a","kind":"tf","answer":true}
]}
```

Al arrancar, el backend:
- valida todos los JSON privados;
- carga examen y recuperación de forma idempotente;
- valida el Portafolio contra su banco público completo;
- guarda un `public_hash` por actividad de Portafolio;
- actualiza las claves privadas del Portafolio si el archivo privado corresponde a la versión pública actual;
- rechaza una evaluación si la actividad pública cambia y la clave privada no ha sido reprovisionada.

Los archivos con respuestas deben copiarse al servidor **fuera de Git** antes de ejecutar `docker compose up -d`. Un archivo inválido impide el arranque para evitar evaluaciones incompletas o desalineadas.

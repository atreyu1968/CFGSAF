# Bancos privados de evaluación GRH0652

Este directorio se monta en el servidor como `/private-banks` en modo solo lectura. Los JSON reales contienen respuestas y **no deben versionarse**.

Cree localmente archivos `*.json` con uno de estos esquemas:

Examen:
```json
{"course_id":"GRH0652_UT1","kind":"exam","questions":[{"id":"e1","ce":"1.a","q":"Enunciado","options":["A","B"],"answer":0,"type":"choice"}]}
```

Recuperación:
```json
{"course_id":"GRH0652_UT1","kind":"recovery","items":[{"id":"r1","ce":"1.a","kind":"choice","prompt":"Enunciado","options":["A","B"],"answer":1,"feedback":"Orientación tras responder"}]}
```

Al arrancar, el backend valida y carga únicamente cursos que todavía no tengan ese tipo de banco en SQLite. Un archivo inválido impide el arranque para evitar evaluaciones incompletas.

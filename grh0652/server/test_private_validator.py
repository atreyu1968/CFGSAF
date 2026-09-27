import json
from pathlib import Path
import validate_private_banks as v

def write(path,data):
 path.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")

def private_answer(item):
 kind=item["kind"];opts=item.get("options") or []
 if kind=="choice":return 0
 if kind=="tf":return True
 if kind=="multi":return [0]
 if kind=="order":return list(range(len(opts)))
 if kind=="match":return list(range(len(item.get("pairs") or [])))
 if kind=="calculation":return 1
 return "Respuesta de referencia suficientemente completa para validación del esquema."

def build_valid(directory):
 for course,(unit,ces) in v.COURSES.items():
  public=json.loads((v.PUBLIC/f"{unit}_portfolio.json").read_text(encoding="utf-8"))["items"]
  write(directory/f"{unit}_portfolio.json",{"course_id":course,"kind":"portfolio","items":[{"id":x["id"],"ce":x["ce"],"kind":x["kind"],"answer":private_answer(x)} for x in public]})
  questions=[]
  for ce in ces:
   for n in range(3):
    questions.append({"id":f"{unit}-exam-{ce}-{n}","ce":ce,"q":"Pregunta privada de validación","options":["Correcta","Distractor"],"answer":0,"type":"choice"})
  write(directory/f"{unit}_exam.json",{"course_id":course,"kind":"exam","questions":questions})
  recovery=[]
  for ce in ces:
   for n in range(2):
    recovery.append({"id":f"{unit}-rec-{ce}-{n}","ce":ce,"kind":"choice","prompt":"Actividad privada de recuperación","options":["Correcta","Distractor"],"answer":0,"feedback":"Revisar el criterio."})
  write(directory/f"{unit}_recovery.json",{"course_id":course,"kind":"recovery","items":recovery})

def test_private_bank_validator_accepts_complete_v1_package(tmp_path):
 build_valid(tmp_path)
 out=v.validate_directory(tmp_path)
 assert set(out)==set(v.COURSES)
 assert out["GRH0652_UT1"]["portfolio"]["items"]==54
 assert all(min(x["exam"]["per_ce"].values())>=3 for x in out.values())
 assert all(min(x["recovery"]["per_ce"].values())>=2 for x in out.values())

def test_private_bank_validator_rejects_missing_portfolio_key(tmp_path):
 build_valid(tmp_path)
 p=tmp_path/"ut2_portfolio.json";d=json.loads(p.read_text(encoding="utf-8"));d["items"].pop();write(p,d)
 try:v.validate_directory(tmp_path)
 except v.ValidationError as e:assert "ids no coinciden" in str(e)
 else:assert False,"Debía rechazar una clave de Portfolio ausente"

def test_private_bank_validator_rejects_shallow_exam_or_recovery(tmp_path):
 build_valid(tmp_path)
 p=tmp_path/"ut3_exam.json";d=json.loads(p.read_text(encoding="utf-8"));d["questions"]=[q for q in d["questions"] if not (q["ce"]=="3.a" and q["id"].endswith("-2"))];write(p,d)
 try:v.validate_directory(tmp_path)
 except v.ValidationError as e:assert "cobertura insuficiente" in str(e)
 else:assert False,"Debía rechazar examen con menos de tres preguntas por CE"

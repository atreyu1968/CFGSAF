#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/"banks"
COURSES={
 "GRH0652_UT1":("ut1",[f"1.{x}" for x in "abcdefghi"]),
 "GRH0652_UT2":("ut2",[f"2.{x}" for x in "abcdef"]),
 "GRH0652_UT3":("ut3",[f"3.{x}" for x in "abcdefgh"]),
 "GRH0652_UT4":("ut4",[f"4.{x}" for x in "abcdefghij"]),
}
OBJECTIVE={"choice","tf","multi","order","match"}
SEMANTIC={"free","text","case","calculation"}
KINDS=OBJECTIVE|SEMANTIC

class ValidationError(RuntimeError):
 pass

def fail(msg):
 raise ValidationError(msg)

def load_json(path):
 try:return json.loads(Path(path).read_text(encoding="utf-8"))
 except Exception as e:fail(f"{path}: JSON inválido: {e}")

def answer_shape(item,answer,where):
 kind=item.get("kind")
 opts=item.get("options") or []
 if kind=="choice":
  if not isinstance(answer,int) or isinstance(answer,bool) or not 0<=answer<len(opts):fail(f"{where}: respuesta choice fuera de rango")
 elif kind=="tf":
  if not isinstance(answer,bool):fail(f"{where}: respuesta tf debe ser booleana")
 elif kind=="multi":
  if not isinstance(answer,list) or not answer:fail(f"{where}: multi sin respuestas")
  if len(set(answer))!=len(answer) or any(not isinstance(x,int) or isinstance(x,bool) or x<0 or x>=len(opts) for x in answer):fail(f"{where}: índices multi inválidos")
 elif kind=="order":
  if not isinstance(answer,list) or len(answer)!=len(opts) or sorted(answer)!=list(range(len(opts))):fail(f"{where}: orden inválido")
 elif kind=="match":
  pairs=item.get("pairs") or []
  if not isinstance(answer,list) or len(answer)!=len(pairs):fail(f"{where}: correspondencia match inválida")
 elif kind=="calculation":
  try:float(str(answer).replace(",","."))
  except Exception:fail(f"{where}: cálculo sin respuesta numérica")
 elif kind in {"free","text","case"}:
  if not isinstance(answer,str) or len(answer.strip())<20:fail(f"{where}: referencia semántica demasiado breve")
 else:fail(f"{where}: tipo no admitido {kind}")

def load_public(course):
 unit,_=COURSES[course]
 data=load_json(PUBLIC/f"{unit}_portfolio.json")
 items=data.get("items") or []
 return {x["id"]:x for x in items}

def validate_portfolio(course,data):
 public=load_public(course)
 items=data.get("items") or []
 if not items:fail(f"{course} portfolio: sin actividades")
 by={x.get("id"):x for x in items}
 if len(by)!=len(items):fail(f"{course} portfolio: ids duplicados")
 if set(by)!=set(public):
  missing=sorted(set(public)-set(by));extra=sorted(set(by)-set(public))
  fail(f"{course} portfolio: ids no coinciden; faltan={missing} sobran={extra}")
 for iid,pub in public.items():
  x=by[iid];where=f"{course} portfolio {iid}"
  if x.get("ce")!=pub.get("ce") or x.get("kind")!=pub.get("kind"):fail(f"{where}: CE/tipo no coincide con banco público")
  answer_shape(pub,x.get("answer"),where)
 return {"items":len(items)}

def validate_exam(course,data,min_per_ce=3):
 _,expected=COURSES[course];questions=data.get("questions") or []
 if not questions:fail(f"{course} exam: sin preguntas")
 ids=set();counts={ce:0 for ce in expected}
 for q in questions:
  qid=str(q.get("id") or "").strip();ce=q.get("ce");typ=q.get("type","choice");where=f"{course} exam {qid or '?'}"
  if not qid or qid in ids:fail(f"{where}: id vacío o duplicado")
  ids.add(qid)
  if ce not in counts:fail(f"{where}: CE no reconocido {ce}")
  if not str(q.get("q") or "").strip():fail(f"{where}: enunciado vacío")
  if typ not in {"choice","tf","multi"}:fail(f"{where}: tipo de examen no admitido {typ}")
  shape={"kind":typ,"options":q.get("options") or []}
  answer_shape(shape,q.get("answer"),where)
  counts[ce]+=1
 missing={ce:n for ce,n in counts.items() if n<min_per_ce}
 if missing:fail(f"{course} exam: cobertura insuficiente {missing}; mínimo {min_per_ce}/CE")
 return {"questions":len(questions),"per_ce":counts}

def validate_recovery(course,data,min_per_ce=2):
 _,expected=COURSES[course];items=data.get("items") or []
 if not items:fail(f"{course} recovery: sin actividades")
 ids=set();counts={ce:0 for ce in expected}
 for x in items:
  iid=str(x.get("id") or "").strip();ce=x.get("ce");kind=x.get("kind");where=f"{course} recovery {iid or '?'}"
  if not iid or iid in ids:fail(f"{where}: id vacío o duplicado")
  ids.add(iid)
  if ce not in counts:fail(f"{where}: CE no reconocido {ce}")
  if kind not in KINDS:fail(f"{where}: tipo no admitido {kind}")
  if not str(x.get("prompt") or "").strip():fail(f"{where}: enunciado vacío")
  answer_shape(x,x.get("answer"),where)
  counts[ce]+=1
 missing={ce:n for ce,n in counts.items() if n<min_per_ce}
 if missing:fail(f"{course} recovery: cobertura insuficiente {missing}; mínimo {min_per_ce}/CE")
 return {"items":len(items),"per_ce":counts}

def validate_directory(directory,min_exam=3,min_recovery=2):
 directory=Path(directory)
 if not directory.is_dir():fail(f"No existe el directorio {directory}")
 docs={}
 for path in sorted(directory.glob("*.json")):
  d=load_json(path);course=d.get("course_id");kind=d.get("kind")
  if course not in COURSES:fail(f"{path.name}: course_id no reconocido {course}")
  if kind not in {"portfolio","exam","recovery"}:fail(f"{path.name}: kind no reconocido {kind}")
  key=(course,kind)
  if key in docs:fail(f"Duplicado {course}/{kind}: {docs[key][0].name} y {path.name}")
  docs[key]=(path,d)
 required={(c,k) for c in COURSES for k in ("portfolio","exam","recovery")}
 missing=sorted(required-set(docs))
 if missing:fail("Faltan bancos: "+", ".join(f"{c}/{k}" for c,k in missing))
 summary={}
 for course in COURSES:
  summary[course]={
   "portfolio":validate_portfolio(course,docs[(course,"portfolio")][1]),
   "exam":validate_exam(course,docs[(course,"exam")][1],min_exam),
   "recovery":validate_recovery(course,docs[(course,"recovery")][1],min_recovery),
  }
 return summary

def main():
 p=argparse.ArgumentParser(description="Valida los bancos privados GRH0652 antes de producción.")
 p.add_argument("directory",help="Directorio con 12 JSON: portfolio, exam y recovery para UT1–UT4")
 p.add_argument("--exam-per-ce",type=int,default=3)
 p.add_argument("--recovery-per-ce",type=int,default=2)
 a=p.parse_args()
 try:
  out=validate_directory(a.directory,a.exam_per_ce,a.recovery_per_ce)
 except ValidationError as e:
  print("ERROR:",e,file=sys.stderr);return 2
 print("OK · bancos privados GRH0652 válidos")
 for course,d in out.items():
  print(f"{course}: portfolio={d['portfolio']['items']} · examen={d['exam']['questions']} · recuperación={d['recovery']['items']}")
 return 0

if __name__=="__main__":
 raise SystemExit(main())

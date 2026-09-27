#!/usr/bin/env python3
"""Chequeo remoto seguro de una instalación GRH0652.

No crea alumnos, no abre exámenes, no modifica notas y no restaura copias.
Comprueba salud, readiness de UT1-UT4, configuración, monitor, exportación
Additio y backup+validación del backup.
"""
import argparse,csv,io,json,os,sys
from pathlib import Path
import httpx

COURSES=("GRH0652_UT1","GRH0652_UT2","GRH0652_UT3","GRH0652_UT4")

class AcceptanceError(RuntimeError):
 pass

def require(cond,msg):
 if not cond: raise AcceptanceError(msg)

def validate_readiness_payload(course,payload):
 require(payload.get("course_id")==course,f"{course}: course_id inesperado")
 checks=payload.get("checks") or {}
 for name in ("students","portfolio_keys","exam_bank","recovery_bank","origins"):
  require(name in checks,f"{course}: falta check {name}")
 require(checks["students"].get("count",0)>0,f"{course}: no hay alumnado cargado")
 pk=checks["portfolio_keys"]
 require(pk.get("ok") is True,f"{course}: claves de Portafolio incompletas/obsoletas: {pk}")
 eb=checks["exam_bank"]
 required=max(1,int(eb.get("required_per_ce",0)))
 for ce in eb.get("expected_ce") or []:
  require(int((eb.get("counts") or {}).get(ce,0))>=required,f"{course}: examen insuficiente en {ce}")
 rb=checks["recovery_bank"]
 rrequired=max(2,int(rb.get("required_per_ce",2)))
 for ce in rb.get("expected_ce") or []:
  require(int((rb.get("counts") or {}).get(ce,0))>=rrequired,f"{course}: recuperación insuficiente en {ce}")
 require(checks["origins"].get("ok") is True,f"{course}: CORS/orígenes no configurados")
 require(payload.get("ready") is True,f"{course}: readiness general no está en verde")
 return True

def validate_additio_csv(data):
 require(data.startswith(b"\xef\xbb\xbf"),"Additio: falta BOM UTF-8")
 text=data.decode("utf-8-sig")
 require("\r\n" in text or "\n" in text,"Additio: CSV sin líneas")
 rows=list(csv.reader(io.StringIO(text,newline=""),delimiter=";"))
 require(rows and rows[0] and rows[0][0]=="Alumno","Additio: cabecera inválida")
 for expected in ("Portafolio","Examen","RA"):
  require(expected in rows[0],f"Additio: falta columna {expected}")
 return {"rows":max(0,len(rows)-1),"columns":len(rows[0])}

def check_response(r,label):
 if r.status_code>=400:
  body=r.text[:1000]
  raise AcceptanceError(f"{label}: HTTP {r.status_code}: {body}")
 return r

def run_acceptance(base_url,token,save_backup=None,timeout=30):
 base=base_url.rstrip("/")
 headers={"X-Teacher-Token":token}
 report={"api":base,"courses":{},"backup":{}}
 with httpx.Client(timeout=timeout,follow_redirects=True) as client:
  health=check_response(client.get(base+"/health"),"health").json()
  require(health.get("ok") is True,"health: respuesta inesperada")
  report["health"]="ok"

  for course in COURSES:
   ready=check_response(client.get(base+f"/api/teacher/readiness/{course}",headers=headers),f"{course} readiness").json()
   validate_readiness_payload(course,ready)
   cfg=check_response(client.get(base+f"/api/teacher/config/{course}",headers=headers),f"{course} config").json()
   for field in ("portfolio_weight","exam_weight","pass_score","ce_pass_percent","ce_pass_score","exam_questions_per_ce","exam_minutes"):
    require(field in cfg,f"{course}: falta configuración {field}")
   require(int(cfg["exam_questions_per_ce"])>=1,f"{course}: exam_questions_per_ce inválido")
   require(1<=int(cfg["exam_minutes"])<=300,f"{course}: exam_minutes inválido")
   mon=check_response(client.get(base+f"/api/teacher/exam-monitor/{course}",headers=headers),f"{course} monitor").json()
   require(mon.get("course_id")==course and "summary" in mon and "attempts" in mon,f"{course}: monitor inválido")
   csv_r=check_response(client.get(base+f"/api/teacher/export-additio/{course}",headers=headers),f"{course} Additio")
   csv_info=validate_additio_csv(csv_r.content)
   report["courses"][course]={
    "ready":True,
    "students":ready["checks"]["students"]["count"],
    "portfolio_keys":ready["checks"]["portfolio_keys"]["count"],
    "exam_per_ce":ready["checks"]["exam_bank"]["counts"],
    "recovery_per_ce":ready["checks"]["recovery_bank"]["counts"],
    "exam_enabled":bool(cfg.get("exam_enabled")),
    "evaluation_closed":bool(cfg.get("evaluation_closed")),
    "monitor":mon.get("summary") or {},
    "additio":csv_info,
   }

  backup=check_response(client.get(base+"/api/teacher/backup",headers=headers),"backup")
  require(backup.content[:16]==b"SQLite format 3\x00","backup: no es SQLite")
  valid=check_response(client.post(base+"/api/teacher/backup/validate",headers=headers,files={"file":("grh0652-backup.db",backup.content,"application/vnd.sqlite3")}),"backup validate").json()
  require(valid.get("ok") is True and valid.get("integrity")=="ok","backup: validación no superada")
  report["backup"]={"bytes":len(backup.content),"integrity":"ok","counts":valid.get("counts") or {}}
  if save_backup:
   p=Path(save_backup)
   p.parent.mkdir(parents=True,exist_ok=True)
   p.write_bytes(backup.content)
   report["backup"]["saved_to"]=str(p)
 return report

def main():
 p=argparse.ArgumentParser(description="Aceptación remota segura de GRH0652 en producción.")
 p.add_argument("--api",default=os.getenv("GRH_API_URL",""),help="URL base del backend; o GRH_API_URL")
 p.add_argument("--token",default=os.getenv("GRH_TEACHER_TOKEN",""),help="Token docente; o GRH_TEACHER_TOKEN")
 p.add_argument("--save-backup",default="",help="Ruta opcional donde conservar la copia descargada")
 p.add_argument("--timeout",type=float,default=30)
 p.add_argument("--json",action="store_true",help="Salida JSON")
 a=p.parse_args()
 if not a.api or not a.token:
  print("ERROR: indique --api y --token o defina GRH_API_URL y GRH_TEACHER_TOKEN",file=sys.stderr)
  return 2
 try:
  report=run_acceptance(a.api,a.token,a.save_backup or None,a.timeout)
 except (AcceptanceError,httpx.HTTPError) as e:
  print("ERROR:",e,file=sys.stderr)
  return 1
 if a.json:print(json.dumps(report,ensure_ascii=False,indent=2))
 else:
  print("OK · GRH0652 supera la aceptación remota segura")
  for course,d in report["courses"].items():
   print(f"{course}: listo · alumnos={d['students']} · portfolio={d['portfolio_keys']} · Additio={d['additio']['rows']} filas")
  print(f"Backup: {report['backup']['integrity']} · {report['backup']['bytes']} bytes")
 return 0

if __name__=="__main__":
 raise SystemExit(main())

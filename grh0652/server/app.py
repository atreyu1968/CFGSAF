import os,json,sqlite3,datetime,secrets
from pathlib import Path
from fastapi import FastAPI,HTTPException,Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB=os.getenv("GRH_DB","grh0652.db")
TEACHER_TOKEN=os.getenv("GRH_TEACHER_TOKEN")
if not TEACHER_TOKEN:
    raise RuntimeError("Define GRH_TEACHER_TOKEN antes de iniciar el servidor")
ORIGINS=[x.strip() for x in os.getenv("GRH_ALLOWED_ORIGINS","").split(",") if x.strip()]
app=FastAPI(title="GRH0652 Evidence API")
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS or [],allow_credentials=False,allow_methods=["GET","POST","PUT"],allow_headers=["Content-Type","X-Teacher-Token"])

def now(): return datetime.datetime.now(datetime.UTC).isoformat()
def con():
 c=sqlite3.connect(DB,timeout=10);c.row_factory=sqlite3.Row;c.execute("PRAGMA journal_mode=WAL");c.execute("PRAGMA foreign_keys=ON");c.execute("PRAGMA busy_timeout=5000")
 c.executescript("""CREATE TABLE IF NOT EXISTS students(student_id TEXT PRIMARY KEY,token TEXT NOT NULL UNIQUE,created_at TEXT);\nCREATE TABLE IF NOT EXISTS states(student_id TEXT,course_id TEXT,state TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT,course_id TEXT,kind TEXT,ce TEXT,item_id TEXT,attempt INTEGER,response TEXT,correct INTEGER,score REAL,payload TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS results(student_id TEXT,course_id TEXT,portfolio REAL,exam REAL,final REAL,ce_passed INTEGER,ce_total INTEGER,ra_passed INTEGER,recovery TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS configs(course_id TEXT PRIMARY KEY,config TEXT,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT NOT NULL,course_id TEXT NOT NULL,kind TEXT NOT NULL,item_id TEXT NOT NULL,attempt_no INTEGER NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,submitted_at TEXT,payload TEXT,UNIQUE(student_id,course_id,kind,item_id,attempt_no));
CREATE TABLE IF NOT EXISTS evaluation_closures(course_id TEXT PRIMARY KEY,closed_at TEXT,config_version INTEGER);
CREATE TABLE IF NOT EXISTS recovery_plans(student_id TEXT,course_id TEXT,criteria TEXT,status TEXT,created_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS exam_banks(course_id TEXT,question_id TEXT,ce TEXT,question TEXT,options TEXT,answer TEXT,type TEXT NOT NULL DEFAULT 'choice',PRIMARY KEY(course_id,question_id));
CREATE TABLE IF NOT EXISTS exam_versions(attempt_id INTEGER PRIMARY KEY,student_id TEXT,course_id TEXT,version TEXT,questions TEXT,answers TEXT,created_at TEXT,config TEXT,deadline_at TEXT);
CREATE TABLE IF NOT EXISTS recovery_banks(course_id TEXT,item_id TEXT,ce TEXT,kind TEXT,prompt TEXT,options TEXT,answer TEXT,feedback TEXT,PRIMARY KEY(course_id,item_id));\nCREATE TABLE IF NOT EXISTS portfolio_banks(course_id TEXT,item_id TEXT,ce TEXT,kind TEXT,answer TEXT,PRIMARY KEY(course_id,item_id));
CREATE TABLE IF NOT EXISTS recovery_results(student_id TEXT,course_id TEXT,score REAL,criteria_passed TEXT,status TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));""")
 cols={r["name"] for r in c.execute("PRAGMA table_info(exam_versions)")}
 if "config" not in cols:c.execute("ALTER TABLE exam_versions ADD COLUMN config TEXT")
 if "deadline_at" not in cols:c.execute("ALTER TABLE exam_versions ADD COLUMN deadline_at TEXT")
 bcols={r["name"] for r in c.execute("PRAGMA table_info(exam_banks)")}
 if "type" not in bcols:c.execute("ALTER TABLE exam_banks ADD COLUMN type TEXT NOT NULL DEFAULT 'choice'")
 # Seed versioned portfolio answer banks from repository without exposing them to the browser.
 if c.execute("SELECT COUNT(*) n FROM portfolio_banks WHERE course_id='GRH0652'").fetchone()["n"]==0:
  bank_dir=Path(__file__).resolve().parent/"banks"
  for unit in ("ut1","ut2","ut3","ut4"):
   p=bank_dir/f"{unit}_portfolio.json"
   if p.exists():
    for q in json.loads(p.read_text(encoding="utf-8")).get("items",[]):
     c.execute("INSERT OR REPLACE INTO portfolio_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("GRH0652",q["id"],q["ce"],q["kind"],json.dumps(q.get("answer"),ensure_ascii=False)))
 c.commit();return c

DEFAULT={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":False,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
LIMITS={"practice":3,"portfolio":2,"exam":1,"recovery":1}
class StateIn(BaseModel): course_id:str;state:dict
class EventIn(BaseModel):
 student_id:str;course_id:str;kind:str;ce:str|None=None;item_id:str|None=None;attempt:int|None=None;response:object|None=None;correct:bool|None=None;score:float|None=None;payload:dict|None=None
class ResultIn(BaseModel): student_id:str;course_id:str;portfolio:float;exam:float;final:float;ce_passed:int;ce_total:int;ra_passed:bool;recovery:list[str]=[]
class ConfigIn(BaseModel):
 portfolio_weight:int=40;exam_weight:int=60;pass_score:float=50;ce_pass_percent:int=80;ce_pass_score:float=50;exam_enabled:bool=False;exam_questions_per_ce:int=3;exam_minutes:int=45;require_both_instruments:bool=False
class AttemptIn(BaseModel): student_id:str;course_id:str;kind:str;item_id:str;payload:dict|None=None
class SubmitAttempt(BaseModel): payload:dict|None=None
class AnswerIn(BaseModel): response:object|None=None;ce:str|None=None
class BankQuestion(BaseModel): id:str;ce:str;q:str;options:list[str]=[];answer:object;type:str='choice'
class BankIn(BaseModel): questions:list[BankQuestion]
class RecoveryItem(BaseModel): id:str;ce:str;kind:str='choice';prompt:str;options:list[str]=[];answer:object|None=None;feedback:str=''
class RecoveryBankIn(BaseModel): items:list[RecoveryItem]
def auth(token):
 if not secrets.compare_digest(token or "",TEACHER_TOKEN): raise HTTPException(401,"Teacher token required")
def config_row(c,course):
 r=c.execute("SELECT config,version FROM configs WHERE course_id=?",(course,)).fetchone()
 return (json.loads(r["config"]),r["version"]) if r else (DEFAULT,0)

@app.get("/health")
def health(): return {"ok":True}
@app.get("/api/config/{course_id}")
def get_config(course_id:str):
 c=con();d,v=config_row(c,course_id);closed=c.execute("SELECT closed_at FROM evaluation_closures WHERE course_id=?",(course_id,)).fetchone();c.close();return {**d,"version":v,"evaluation_closed":bool(closed)}
@app.put("/api/config/{course_id}")
def put_config(course_id:str,x:ConfigIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);d=x.model_dump()
 if d["portfolio_weight"]+d["exam_weight"]!=100: raise HTTPException(400,"Los pesos deben sumar 100")
 c=con()
 if c.execute("SELECT 1 FROM evaluation_closures WHERE course_id=?",(course_id,)).fetchone(): c.close();raise HTTPException(409,"La evaluación está cerrada")
 _,v=config_row(c,course_id);v+=1;c.execute("INSERT OR REPLACE INTO configs(course_id,config,version,updated_at) VALUES(?,?,?,?)",(course_id,json.dumps(d),v,now()));c.commit();c.close();return {**d,"version":v}
@app.post("/api/attempts/start")
def start_attempt(x:AttemptIn):
 if x.kind not in LIMITS: raise HTTPException(400,"Tipo de intento no válido")
 c=con();c.execute("BEGIN IMMEDIATE")
 active=c.execute("SELECT * FROM attempts WHERE student_id=? AND course_id=? AND kind=? AND item_id=? AND status='started' ORDER BY attempt_no DESC LIMIT 1",(x.student_id,x.course_id,x.kind,x.item_id)).fetchone()
 if active: c.commit();c.close();return {"id":active["id"],"attempt":active["attempt_no"],"status":"started","resumed":True}
 n=c.execute("SELECT COUNT(*) n FROM attempts WHERE student_id=? AND course_id=? AND kind=? AND item_id=?",(x.student_id,x.course_id,x.kind,x.item_id)).fetchone()["n"]
 if n>=LIMITS[x.kind]: c.rollback();c.close();raise HTTPException(409,"Límite de intentos alcanzado")
 if x.kind=="exam":
  cfg,_=config_row(c,x.course_id)
  if not cfg.get("exam_enabled"): c.rollback();c.close();raise HTTPException(403,"Examen no activado")
  if c.execute("SELECT 1 FROM evaluation_closures WHERE course_id=?",(x.course_id,)).fetchone(): c.rollback();c.close();raise HTTPException(409,"Evaluación cerrada")
 n+=1;c.execute("INSERT INTO attempts(student_id,course_id,kind,item_id,attempt_no,status,started_at,payload) VALUES(?,?,?,?,?,'started',?,?)",(x.student_id,x.course_id,x.kind,x.item_id,n,now(),json.dumps(x.payload or {},ensure_ascii=False)));aid=c.execute("SELECT last_insert_rowid() id").fetchone()["id"];c.commit();c.close();return {"id":aid,"attempt":n,"status":"started","resumed":False}
@app.post("/api/attempts/{attempt_id}/submit")
def submit_attempt(attempt_id:int,x:SubmitAttempt):
 c=con();r=c.execute("SELECT status FROM attempts WHERE id=?",(attempt_id,)).fetchone()
 if not r:c.close();raise HTTPException(404,"Intento no encontrado")
 if r["status"]!="started":c.close();raise HTTPException(409,"Intento ya entregado")
 c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps(x.payload or {},ensure_ascii=False),attempt_id));c.commit();c.close();return {"ok":True}
@app.post("/api/attempts/{attempt_id}/answer")
def answer_attempt(attempt_id:int,x:AnswerIn):
 c=con();c.execute("BEGIN IMMEDIATE");r=c.execute("SELECT * FROM attempts WHERE id=?",(attempt_id,)).fetchone()
 if not r: c.rollback();c.close();raise HTTPException(404,"Intento no encontrado")
 if r["status"]!="started": c.rollback();c.close();raise HTTPException(409,"Intento cerrado")
 p=json.loads(r["payload"] or "{}");p["response"]=x.response
 c.execute("UPDATE attempts SET payload=? WHERE id=?",(json.dumps(p,ensure_ascii=False),attempt_id))
 c.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(r["student_id"],r["course_id"],r["kind"],x.ce,r["item_id"],r["attempt_no"],json.dumps(x.response,ensure_ascii=False),json.dumps({"server_attempt_id":attempt_id}),now()))
 c.commit();c.close();return {"ok":True,"attempt":r["attempt_no"]}

@app.get("/api/recovery/{student_id}/{course_id}")
def recovery(student_id:str,course_id:str):
 c=con();r=c.execute("SELECT criteria,status,created_at FROM recovery_plans WHERE student_id=? AND course_id=?",(student_id,course_id)).fetchone();c.close()
 if not r:return {"plan":None}
 return {"plan":{"criteria":json.loads(r["criteria"] or "[]"),"status":r["status"],"created_at":r["created_at"]}}

@app.put("/api/teacher/recovery-bank/{course_id}")
def put_recovery_bank(course_id:str,x:RecoveryBankIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();c.execute("DELETE FROM recovery_banks WHERE course_id=?",(course_id,))
 for i in x.items:c.execute("INSERT INTO recovery_banks VALUES(?,?,?,?,?,?,?,?)",(course_id,i.id,i.ce,i.kind,i.prompt,json.dumps(i.options,ensure_ascii=False),json.dumps(i.answer,ensure_ascii=False),i.feedback))
 c.commit();c.close();return {"items":len(x.items)}

@app.get("/api/recovery/{student_id}/{course_id}/content")
def recovery_content(student_id:str,course_id:str):
 c=con();p=c.execute("SELECT criteria,status FROM recovery_plans WHERE student_id=? AND course_id=?",(student_id,course_id)).fetchone()
 if not p:c.close();return {"plan":None}
 ces=json.loads(p["criteria"] or "[]");rows=[dict(r) for r in c.execute("SELECT item_id,ce,kind,prompt,options,feedback FROM recovery_banks WHERE course_id=? ORDER BY ce,item_id",(course_id,)) if r["ce"] in ces];c.close()
 for r in rows:r["options"]=json.loads(r["options"] or "[]")
 return {"plan":{"criteria":ces,"status":p["status"],"items":rows}}

@app.post("/api/recovery/start")
def recovery_start(x:AttemptIn):
 c=con();p=c.execute("SELECT criteria,status FROM recovery_plans WHERE student_id=? AND course_id=?",(x.student_id,x.course_id)).fetchone();c.close()
 if not p:raise HTTPException(403,"No existe plan de recuperación")
 x.kind="recovery";x.item_id="recovery-final";return start_attempt(x)

@app.post("/api/recovery/{attempt_id}/submit")
def recovery_submit(attempt_id:int,x:SubmitAttempt):
 c=con();a=c.execute("SELECT * FROM attempts WHERE id=?",(attempt_id,)).fetchone()
 if not a or a["kind"]!="recovery":c.close();raise HTTPException(404,"Intento de recuperación no encontrado")
 if a["status"]!="started":c.close();raise HTTPException(409,"Recuperación ya entregada")
 p=c.execute("SELECT criteria,status FROM recovery_plans WHERE student_id=? AND course_id=?",(a["student_id"],a["course_id"])).fetchone()
 if not p or p["status"]!="pending":
  c.close();raise HTTPException(409,"Plan de recuperación no disponible")
 cfg,_=config_row(c,a["course_id"])
 threshold=float(cfg.get("ce_pass_score",50))/100.0
 ces=json.loads(p["criteria"] or "[]")
 answers=(x.payload or {}).get("answers",{});rows=[dict(r) for r in c.execute("SELECT * FROM recovery_banks WHERE course_id=?",(a["course_id"],)) if r["ce"] in ces];by={}
 for r in rows:
  d=by.setdefault(r["ce"],{"ok":0,"n":0});d["n"]+=1;given=answers.get(r["item_id"]);expected=json.loads(r["answer"]);kind=r["kind"] or "choice"
  if kind=="multi" and isinstance(given,list) and isinstance(expected,list):ok=sorted(given)==sorted(expected)
  elif kind=="free":ok=str(given or "").strip().casefold()==str(expected or "").strip().casefold()
  else:ok=given==expected
  if ok:d["ok"]+=1
 passed=[ce for ce,v in by.items() if v["n"] and v["ok"]/v["n"]>=threshold];score=round(sum(v["ok"] for v in by.values())/max(1,sum(v["n"] for v in by.values()))*100,2);status="passed" if len(passed)==len(ces) else "pending"
 c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps({"answers":answers,"score":score,"by_ce":by},ensure_ascii=False),attempt_id));c.execute("INSERT OR REPLACE INTO recovery_results VALUES(?,?,?,?,?,?)",(a["student_id"],a["course_id"],score,json.dumps(passed),status,now()))
 rr=c.execute("SELECT * FROM results WHERE student_id=? AND course_id=?",(a["student_id"],a["course_id"])).fetchone()
 authoritative=None
 if rr:
  old_pending=json.loads(rr["recovery"] or "[]");remaining=[ce for ce in old_pending if ce not in passed];new_passed=int(rr["ce_passed"])+sum(1 for ce in passed if ce in old_pending);total=int(rr["ce_total"]);needed=(total*int(cfg["ce_pass_percent"])+99)//100
  ra=bool(float(rr["final"])>=float(cfg["pass_score"]) and new_passed>=needed)
  c.execute("UPDATE results SET ce_passed=?,ra_passed=?,recovery=?,updated_at=? WHERE student_id=? AND course_id=?",(new_passed,int(ra),json.dumps(remaining),now(),a["student_id"],a["course_id"]))
  status="passed" if not remaining else "pending";authoritative={"ce_passed":new_passed,"ce_total":total,"ra_passed":ra,"recovery":remaining}
 c.execute("UPDATE recovery_plans SET criteria=?,status=? WHERE student_id=? AND course_id=?",(json.dumps(authoritative["recovery"] if authoritative else [ce for ce in ces if ce not in passed]),status,a["student_id"],a["course_id"]));c.commit();c.close();return {"score":score,"by_ce":by,"criteria_passed":passed,"status":status,"result":authoritative}

@app.put("/api/teacher/portfolio-bank/{course_id}")
def put_portfolio_bank(course_id:str,x:RecoveryBankIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();c.execute("DELETE FROM portfolio_banks WHERE course_id=?",(course_id,))
 for q in x.items:
  if q.kind not in ("choice","tf","multi","free","order","match"):c.close();raise HTTPException(400,"Tipo de actividad no válido")
  c.execute("INSERT INTO portfolio_banks VALUES(?,?,?,?,?)",(course_id,q.id,q.ce,q.kind,json.dumps(q.answer,ensure_ascii=False)))
 c.commit();c.close();return {"ok":True,"items":len(x.items)}

@app.put("/api/teacher/exam-bank/{course_id}")
def put_exam_bank(course_id:str,x:BankIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();c.execute("DELETE FROM exam_banks WHERE course_id=?",(course_id,))
 for q in x.questions:
  if q.type not in ("choice","tf","multi"):c.close();raise HTTPException(400,"Tipo de pregunta no válido")
  if q.type=="choice" and (not isinstance(q.answer,int) or isinstance(q.answer,bool) or q.answer<0 or q.answer>=len(q.options)):c.close();raise HTTPException(400,"Respuesta choice no válida")
  if q.type=="tf" and not isinstance(q.answer,bool):c.close();raise HTTPException(400,"Respuesta tf no válida")
  if q.type=="multi" and (not isinstance(q.answer,list) or not q.answer or any(not isinstance(i,int) or isinstance(i,bool) or i<0 or i>=len(q.options) for i in q.answer)):c.close();raise HTTPException(400,"Respuesta multi no válida")
  c.execute("INSERT INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",(course_id,q.id,q.ce,q.q,json.dumps(q.options,ensure_ascii=False),json.dumps(q.answer,ensure_ascii=False),q.type))
 c.commit();c.close();return {"questions":len(x.questions)}

@app.post("/api/exam/start")
def exam_start(x:AttemptIn):
 if x.kind!="exam": raise HTTPException(400,"kind debe ser exam")
 c=con();active=c.execute("SELECT id,attempt_no FROM attempts WHERE student_id=? AND course_id=? AND kind='exam' AND item_id=? AND status='started' ORDER BY attempt_no DESC LIMIT 1",(x.student_id,x.course_id,x.item_id)).fetchone()
 if active:
  old=c.execute("SELECT * FROM exam_versions WHERE attempt_id=?",(active["id"],)).fetchone()
  if old:c.close();return {"attempt_id":active["id"],"attempt":active["attempt_no"],"version":old["version"],"questions":json.loads(old["questions"]),"config":json.loads(old["config"]) if old["config"] else {},"deadline_at":old["deadline_at"],"resumed":True}
 cfg,_=config_row(c,x.course_id)
 if not cfg.get("exam_enabled"):c.close();raise HTTPException(403,"Examen no activado")
 if c.execute("SELECT 1 FROM evaluation_closures WHERE course_id=?",(x.course_id,)).fetchone():c.close();raise HTTPException(409,"Evaluación cerrada")
 rows=[dict(r) for r in c.execute("SELECT * FROM exam_banks WHERE course_id=? ORDER BY ce,question_id",(x.course_id,))]
 if not rows:c.close();raise HTTPException(409,"Banco de examen no cargado en el servidor")
 c.close();gate=start_attempt(x);c=con()
 import random,hashlib
 seed=int(hashlib.sha256((x.student_id+"|"+x.course_id+"|"+str(gate["id"])).encode()).hexdigest()[:16],16);rnd=random.Random(seed);by={}
 for r in rows:by.setdefault(r["ce"],[]).append(r)
 chosen=[]
 for ce,a in by.items():rnd.shuffle(a);chosen+=a[:max(1,int(cfg.get("exam_questions_per_ce",3)))]
 rnd.shuffle(chosen);public=[];keys={}
 for r in chosen:
  kind=r["type"] or "choice";opts=json.loads(r["options"]);correct=json.loads(r["answer"])
  if kind=="tf":
   public.append({"id":r["question_id"],"ce":r["ce"],"q":r["question"],"options":[],"type":"tf"});keys[r["question_id"]]=correct
  else:
   pairs=list(enumerate(opts));rnd.shuffle(pairs);public.append({"id":r["question_id"],"ce":r["ce"],"q":r["question"],"options":[p[1] for p in pairs],"type":kind})
   if kind=="multi":keys[r["question_id"]]=sorted(pairs.index(next(p for p in pairs if p[0]==i)) for i in correct)
   else:keys[r["question_id"]]=pairs.index(next(p for p in pairs if p[0]==correct))
 version=secrets.token_hex(8)
 created=now()
 deadline=(datetime.datetime.fromisoformat(created)+datetime.timedelta(minutes=max(1,int(cfg.get("exam_minutes",45))))).isoformat()
 snap=json.dumps(cfg,ensure_ascii=False)
 c.execute("INSERT INTO exam_versions(attempt_id,student_id,course_id,version,questions,answers,created_at,config,deadline_at) VALUES(?,?,?,?,?,?,?,?,?)",(gate["id"],x.student_id,x.course_id,version,json.dumps(public,ensure_ascii=False),json.dumps(keys),created,snap,deadline))
 c.commit();c.close();return {"attempt_id":gate["id"],"attempt":gate["attempt"],"version":version,"questions":public,"config":cfg,"deadline_at":deadline,"resumed":False}

@app.post("/api/exam/{attempt_id}/submit")
def exam_submit(attempt_id:int,x:SubmitAttempt):
 c=con();v=c.execute("SELECT * FROM exam_versions WHERE attempt_id=?",(attempt_id,)).fetchone();a=c.execute("SELECT * FROM attempts WHERE id=?",(attempt_id,)).fetchone()
 if not v or not a:c.close();raise HTTPException(404,"Examen no encontrado")
 if a["status"]!="started":c.close();raise HTTPException(409,"Examen ya entregado")
 if v["deadline_at"] and datetime.datetime.now(datetime.timezone.utc)>datetime.datetime.fromisoformat(v["deadline_at"]):
  c.execute("UPDATE attempts SET status='expired',submitted_at=? WHERE id=?",(now(),attempt_id));c.commit();c.close();raise HTTPException(410,"Tiempo de examen agotado")
 answers=(x.payload or {}).get("answers",{});keys=json.loads(v["answers"]);questions=json.loads(v["questions"]);by={};good=0
 for q in questions:
  given=answers.get(q["id"]);expected=keys.get(q["id"]);ok=(sorted(given)==expected if q.get("type")=="multi" and isinstance(given,list) else given==expected);good+=int(ok);d=by.setdefault(q["ce"],{"ok":0,"n":0});d["n"]+=1;d["ok"]+=int(ok)
 score=round(good/max(1,len(questions))*100,2);c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps({"answers":answers,"score":score,"by_ce":by},ensure_ascii=False),attempt_id));c.commit();c.close();return {"score":score,"by_ce":by,"answered":len(answers),"total":len(questions)}

@app.put("/api/state/{student_id}")
def put_state(student_id:str,x:StateIn):
 c=con();c.execute("INSERT OR REPLACE INTO states VALUES(?,?,?,?)",(student_id,x.course_id,json.dumps(x.state),now()));c.commit();c.close();return {"ok":True}
@app.get("/api/state/{student_id}")
def get_state(student_id:str,course_id:str):
 c=con();r=c.execute("SELECT state FROM states WHERE student_id=? AND course_id=?",(student_id,course_id)).fetchone();c.close();return {"state":json.loads(r["state"])} if r else {"state":None}
@app.post("/api/evidence")
def evidence(x:EventIn):
 c=con();correct=x.correct;score=x.score
 if x.kind=="portfolio":
  key=c.execute("SELECT ce,kind,answer FROM portfolio_banks WHERE course_id=? AND item_id=?",(x.course_id,x.item_id)).fetchone()
  if not key:c.close();raise HTTPException(409,"Actividad de portafolio no definida en el banco autoritativo")
  if x.ce!=key["ce"]:c.close();raise HTTPException(409,"CE de portafolio no coincide con la definición autoritativa")
  expected=json.loads(key["answer"]);given=x.response;kind=key["kind"] or "choice"
  if kind=="multi" and isinstance(given,list) and isinstance(expected,list):ok=sorted(given)==sorted(expected)
  elif kind=="free":ok=str(given or "").strip().casefold()==str(expected or "").strip().casefold()
  elif kind=="order":ok=given==expected
  elif kind=="match":ok=given==expected
  else:ok=given==expected
  correct=ok;score=100 if ok else 0
 c.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,correct,score,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,x.kind,x.ce,x.item_id,x.attempt,json.dumps(x.response,ensure_ascii=False),None if correct is None else int(correct),score,json.dumps(x.payload or {},ensure_ascii=False),now()));c.commit();c.close();return {"ok":True,"correct":correct,"score":score}
@app.post("/api/result")
def result(x:ResultIn):
 c=con();cfg,_=config_row(c,x.course_id)
 er=c.execute("SELECT payload FROM attempts WHERE student_id=? AND course_id=? AND kind='exam' AND status='submitted' ORDER BY attempt_no DESC LIMIT 1",(x.student_id,x.course_id)).fetchone()
 if not er:c.close();raise HTTPException(409,"No existe examen evaluable entregado")
 ep=json.loads(er["payload"] or "{}");exam_by=ep.get("by_ce",{})
 rows=c.execute("SELECT ce,item_id,attempt,score FROM evidence WHERE student_id=? AND course_id=? AND kind='portfolio' AND ce IS NOT NULL AND score IS NOT NULL ORDER BY id",(x.student_id,x.course_id)).fetchall();latest={}
 for r in rows:
  k=(r["ce"],r["item_id"]);prev=latest.get(k)
  if not prev or int(r["attempt"] or 0)>=int(prev["attempt"] or 0):latest[k]=dict(r)
 portfolio_by={}
 for r in latest.values():portfolio_by.setdefault(r["ce"],[]).append(float(r["score"] or 0))
 expected=[r["ce"] for r in c.execute("SELECT DISTINCT ce FROM exam_banks WHERE course_id=? AND ce IS NOT NULL AND ce<>'' ORDER BY ce",(x.course_id,)).fetchall()]
 if not expected:c.close();raise HTTPException(409,"No existe definición autoritativa de criterios de evaluación")
 observed=set(portfolio_by)|set(exam_by);unexpected=sorted(observed-set(expected))
 if unexpected:c.close();raise HTTPException(409,"Evidencias con criterios no definidos en el banco autoritativo: "+", ".join(unexpected))
 ces=expected
 ce={};pw=float(cfg["portfolio_weight"])/100;ew=float(cfg["exam_weight"])/100
 for ceid in ces:
  ps=portfolio_by.get(ceid,[]);p=sum(ps)/len(ps) if ps else 0;ex=exam_by.get(ceid,{});ev=(float(ex.get("ok",0))/max(1,int(ex.get("n",0)))*100) if ex.get("n",0) else 0;fv=p*pw+ev*ew;ce[ceid]={"portfolio":round(p,2),"exam":round(ev,2),"final":round(fv,2),"passed":fv>=float(cfg["ce_pass_score"])}
 vals=list(ce.values());portfolio=sum(v["portfolio"] for v in vals)/len(vals);exam=sum(v["exam"] for v in vals)/len(vals);final=portfolio*pw+exam*ew;passed=sum(1 for v in vals if v["passed"]);needed=(len(vals)*int(cfg["ce_pass_percent"])+99)//100;both=(not cfg.get("require_both_instruments")) or (portfolio>=float(cfg["pass_score"]) and exam>=float(cfg["pass_score"]));ra=final>=float(cfg["pass_score"]) and passed>=needed and both;recovery=[k for k,v in ce.items() if not v["passed"]]
 c.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,portfolio,exam,final,passed,len(vals),int(ra),json.dumps(recovery),now()));c.commit();c.close();return {"ok":True,"portfolio":round(portfolio,2),"exam":round(exam,2),"final":round(final,2),"ce_passed":passed,"ce_total":len(vals),"ra_passed":ra,"recovery":recovery,"ce":ce}

@app.post("/api/teacher/close/{course_id}")
def close_eval(course_id:str,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();_,v=config_row(c,course_id);c.execute("INSERT OR REPLACE INTO evaluation_closures VALUES(?,?,?)",(course_id,now(),v))
 rows=c.execute("SELECT student_id,recovery FROM results WHERE course_id=? AND ra_passed=0",(course_id,)).fetchall()
 for r in rows:c.execute("INSERT OR REPLACE INTO recovery_plans VALUES(?,?,?,?,?)",(r["student_id"],course_id,r["recovery"],"pending",now()))
 c.commit();c.close();return {"closed":True,"recovery_plans":len(rows),"config_version":v}
@app.get("/api/teacher/overview")
def overview(x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();rows=[dict(r) for r in c.execute("SELECT * FROM results ORDER BY course_id,student_id")];c.close()
 for r in rows:r["recovery"]=json.loads(r["recovery"] or "[]")
 return rows
@app.get("/api/teacher/evidence/{student_id}")
def student_evidence(student_id:str,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();rows=[dict(r) for r in c.execute("SELECT * FROM evidence WHERE student_id=? ORDER BY id",(student_id,))];c.close();return rows

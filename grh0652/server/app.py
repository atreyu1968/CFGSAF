import os,json,sqlite3,datetime,secrets
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
 c.executescript("""CREATE TABLE IF NOT EXISTS states(student_id TEXT,course_id TEXT,state TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT,course_id TEXT,kind TEXT,ce TEXT,item_id TEXT,attempt INTEGER,response TEXT,correct INTEGER,score REAL,payload TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS results(student_id TEXT,course_id TEXT,portfolio REAL,exam REAL,final REAL,ce_passed INTEGER,ce_total INTEGER,ra_passed INTEGER,recovery TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS configs(course_id TEXT PRIMARY KEY,config TEXT,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT);
CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT NOT NULL,course_id TEXT NOT NULL,kind TEXT NOT NULL,item_id TEXT NOT NULL,attempt_no INTEGER NOT NULL,status TEXT NOT NULL,started_at TEXT NOT NULL,submitted_at TEXT,payload TEXT,UNIQUE(student_id,course_id,kind,item_id,attempt_no));
CREATE TABLE IF NOT EXISTS evaluation_closures(course_id TEXT PRIMARY KEY,closed_at TEXT,config_version INTEGER);
CREATE TABLE IF NOT EXISTS recovery_plans(student_id TEXT,course_id TEXT,criteria TEXT,status TEXT,created_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS exam_banks(course_id TEXT,question_id TEXT,ce TEXT,question TEXT,options TEXT,answer TEXT,PRIMARY KEY(course_id,question_id));
CREATE TABLE IF NOT EXISTS exam_versions(attempt_id INTEGER PRIMARY KEY,student_id TEXT,course_id TEXT,version TEXT,questions TEXT,answers TEXT,created_at TEXT,config TEXT,deadline_at TEXT);
CREATE TABLE IF NOT EXISTS recovery_banks(course_id TEXT,item_id TEXT,ce TEXT,kind TEXT,prompt TEXT,options TEXT,answer TEXT,feedback TEXT,PRIMARY KEY(course_id,item_id));
CREATE TABLE IF NOT EXISTS recovery_results(student_id TEXT,course_id TEXT,score REAL,criteria_passed TEXT,status TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));""")
 cols={r["name"] for r in c.execute("PRAGMA table_info(exam_versions)")}
 if "config" not in cols:c.execute("ALTER TABLE exam_versions ADD COLUMN config TEXT")
 if "deadline_at" not in cols:c.execute("ALTER TABLE exam_versions ADD COLUMN deadline_at TEXT")
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
class BankQuestion(BaseModel): id:str;ce:str;q:str;options:list[str];answer:object
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
 p=c.execute("SELECT criteria FROM recovery_plans WHERE student_id=? AND course_id=?",(a["student_id"],a["course_id"])).fetchone();ces=json.loads(p["criteria"] or "[]");answers=(x.payload or {}).get("answers",{});rows=[dict(r) for r in c.execute("SELECT * FROM recovery_banks WHERE course_id=?",(a["course_id"],)) if r["ce"] in ces];by={}
 for r in rows:
  d=by.setdefault(r["ce"],{"ok":0,"n":0});d["n"]+=1
  if answers.get(r["item_id"])==json.loads(r["answer"]):d["ok"]+=1
 passed=[ce for ce,v in by.items() if v["n"] and v["ok"]/v["n"]>=.5];score=round(sum(v["ok"] for v in by.values())/max(1,sum(v["n"] for v in by.values()))*100,2);status="passed" if len(passed)==len(ces) else "pending"
 c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps({"answers":answers,"score":score,"by_ce":by},ensure_ascii=False),attempt_id));c.execute("INSERT OR REPLACE INTO recovery_results VALUES(?,?,?,?,?,?)",(a["student_id"],a["course_id"],score,json.dumps(passed),status,now()));c.execute("UPDATE recovery_plans SET status=? WHERE student_id=? AND course_id=?",(status,a["student_id"],a["course_id"]));c.commit();c.close();return {"score":score,"by_ce":by,"criteria_passed":passed,"status":status}

@app.put("/api/teacher/exam-bank/{course_id}")
def put_exam_bank(course_id:str,x:BankIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();c.execute("DELETE FROM exam_banks WHERE course_id=?",(course_id,))
 for q in x.questions:c.execute("INSERT INTO exam_banks VALUES(?,?,?,?,?,?)",(course_id,q.id,q.ce,q.q,json.dumps(q.options,ensure_ascii=False),json.dumps(q.answer,ensure_ascii=False)))
 c.commit();c.close();return {"questions":len(x.questions)}

@app.post("/api/exam/start")
def exam_start(x:AttemptIn):
 if x.kind!="exam": raise HTTPException(400,"kind debe ser exam")
 gate=start_attempt(x);c=con();old=c.execute("SELECT * FROM exam_versions WHERE attempt_id=?",(gate["id"],)).fetchone()
 if old:c.close();return {"attempt_id":gate["id"],"attempt":gate["attempt"],"version":old["version"],"questions":json.loads(old["questions"]),"config":json.loads(old["config"]) if old["config"] else {},"deadline_at":old["deadline_at"],"resumed":True}
 cfg,_=config_row(c,x.course_id);rows=[dict(r) for r in c.execute("SELECT * FROM exam_banks WHERE course_id=? ORDER BY ce,question_id",(x.course_id,))]
 if not rows:c.close();raise HTTPException(409,"Banco de examen no cargado en el servidor")
 import random,hashlib
 seed=int(hashlib.sha256((x.student_id+"|"+x.course_id+"|"+str(gate["id"])).encode()).hexdigest()[:16],16);rnd=random.Random(seed);by={}
 for r in rows:by.setdefault(r["ce"],[]).append(r)
 chosen=[]
 for ce,a in by.items():rnd.shuffle(a);chosen+=a[:max(1,int(cfg.get("exam_questions_per_ce",3)))]
 rnd.shuffle(chosen);public=[];keys={}
 for r in chosen:
  opts=json.loads(r["options"]);correct=json.loads(r["answer"]);pairs=list(enumerate(opts));rnd.shuffle(pairs);public.append({"id":r["question_id"],"ce":r["ce"],"q":r["question"],"options":[p[1] for p in pairs]});keys[r["question_id"]]=pairs.index(next(p for p in pairs if p[0]==correct))
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
  ok=answers.get(q["id"])==keys.get(q["id"]);good+=int(ok);d=by.setdefault(q["ce"],{"ok":0,"n":0});d["n"]+=1;d["ok"]+=int(ok)
 score=round(good/max(1,len(questions))*100,2);c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps({"answers":answers,"score":score,"by_ce":by},ensure_ascii=False),attempt_id));c.commit();c.close();return {"score":score,"by_ce":by,"answered":len(answers),"total":len(questions)}

@app.put("/api/state/{student_id}")
def put_state(student_id:str,x:StateIn):
 c=con();c.execute("INSERT OR REPLACE INTO states VALUES(?,?,?,?)",(student_id,x.course_id,json.dumps(x.state),now()));c.commit();c.close();return {"ok":True}
@app.get("/api/state/{student_id}")
def get_state(student_id:str,course_id:str):
 c=con();r=c.execute("SELECT state FROM states WHERE student_id=? AND course_id=?",(student_id,course_id)).fetchone();c.close();return {"state":json.loads(r["state"])} if r else {"state":None}
@app.post("/api/evidence")
def evidence(x:EventIn):
 c=con();c.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,correct,score,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,x.kind,x.ce,x.item_id,x.attempt,json.dumps(x.response,ensure_ascii=False),None if x.correct is None else int(x.correct),x.score,json.dumps(x.payload or {},ensure_ascii=False),now()));c.commit();c.close();return {"ok":True}
@app.post("/api/result")
def result(x:ResultIn):
 c=con();c.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,x.portfolio,x.exam,x.final,x.ce_passed,x.ce_total,int(x.ra_passed),json.dumps(x.recovery),now()));c.commit();c.close();return {"ok":True}
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

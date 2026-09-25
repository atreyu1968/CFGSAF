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
CREATE TABLE IF NOT EXISTS recovery_plans(student_id TEXT,course_id TEXT,criteria TEXT,status TEXT,created_at TEXT,PRIMARY KEY(student_id,course_id));""");return c

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
 if active: c.commit();c.close();return {"attempt":active["attempt_no"],"status":"started","resumed":True}
 n=c.execute("SELECT COUNT(*) n FROM attempts WHERE student_id=? AND course_id=? AND kind=? AND item_id=?",(x.student_id,x.course_id,x.kind,x.item_id)).fetchone()["n"]
 if n>=LIMITS[x.kind]: c.rollback();c.close();raise HTTPException(409,"Límite de intentos alcanzado")
 if x.kind=="exam":
  cfg,_=config_row(c,x.course_id)
  if not cfg.get("exam_enabled"): c.rollback();c.close();raise HTTPException(403,"Examen no activado")
  if c.execute("SELECT 1 FROM evaluation_closures WHERE course_id=?",(x.course_id,)).fetchone(): c.rollback();c.close();raise HTTPException(409,"Evaluación cerrada")
 n+=1;c.execute("INSERT INTO attempts(student_id,course_id,kind,item_id,attempt_no,status,started_at,payload) VALUES(?,?,?,?,?,'started',?,?)",(x.student_id,x.course_id,x.kind,x.item_id,n,now(),json.dumps(x.payload or {},ensure_ascii=False)));c.commit();c.close();return {"attempt":n,"status":"started","resumed":False}
@app.post("/api/attempts/{attempt_id}/submit")
def submit_attempt(attempt_id:int,x:SubmitAttempt):
 c=con();r=c.execute("SELECT status FROM attempts WHERE id=?",(attempt_id,)).fetchone()
 if not r:c.close();raise HTTPException(404,"Intento no encontrado")
 if r["status"]!="started":c.close();raise HTTPException(409,"Intento ya entregado")
 c.execute("UPDATE attempts SET status='submitted',submitted_at=?,payload=? WHERE id=?",(now(),json.dumps(x.payload or {},ensure_ascii=False),attempt_id));c.commit();c.close();return {"ok":True}
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

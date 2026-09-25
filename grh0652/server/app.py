import os,json,sqlite3,datetime,math
from fastapi import FastAPI,HTTPException,Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
DB=os.getenv("GRH_DB","grh0652.db"); TEACHER_TOKEN=os.getenv("GRH_TEACHER_TOKEN","cambiar-esta-clave")
app=FastAPI(title="GRH0652 Evidence API")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=False,allow_methods=["*"],allow_headers=["*"])
def con():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row
 c.executescript("""CREATE TABLE IF NOT EXISTS states(student_id TEXT,course_id TEXT,state TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS evidence(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id TEXT,course_id TEXT,kind TEXT,ce TEXT,item_id TEXT,attempt INTEGER,response TEXT,correct INTEGER,score REAL,payload TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS results(student_id TEXT,course_id TEXT,portfolio REAL,exam REAL,final REAL,ce_passed INTEGER,ce_total INTEGER,ra_passed INTEGER,recovery TEXT,updated_at TEXT,PRIMARY KEY(student_id,course_id));
CREATE TABLE IF NOT EXISTS configs(course_id TEXT PRIMARY KEY,config TEXT,updated_at TEXT);""");return c
DEFAULT={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":False,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
class StateIn(BaseModel): course_id:str;state:dict
class EventIn(BaseModel):
 student_id:str;course_id:str;kind:str;ce:str|None=None;item_id:str|None=None;attempt:int|None=None;response:object|None=None;correct:bool|None=None;score:float|None=None;payload:dict|None=None
class ResultIn(BaseModel): student_id:str;course_id:str;portfolio:float;exam:float;final:float;ce_passed:int;ce_total:int;ra_passed:bool;recovery:list[str]=[]
class ConfigIn(BaseModel):
 portfolio_weight:int=40;exam_weight:int=60;pass_score:float=50;ce_pass_percent:int=80;ce_pass_score:float=50;exam_enabled:bool=False;exam_questions_per_ce:int=3;exam_minutes:int=45;require_both_instruments:bool=False
def auth(x_teacher_token): 
 if x_teacher_token!=TEACHER_TOKEN: raise HTTPException(401,"Teacher token required")
@app.get("/health")
def health(): return {"ok":True}
@app.get("/api/config/{course_id}")
def get_config(course_id:str):
 c=con();r=c.execute("SELECT config FROM configs WHERE course_id=?",(course_id,)).fetchone();c.close();return json.loads(r["config"]) if r else DEFAULT
@app.put("/api/config/{course_id}")
def put_config(course_id:str,x:ConfigIn,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);d=x.model_dump()
 if d["portfolio_weight"]+d["exam_weight"]!=100: raise HTTPException(400,"Los pesos deben sumar 100")
 c=con();c.execute("INSERT OR REPLACE INTO configs VALUES(?,?,?)",(course_id,json.dumps(d),datetime.datetime.now(datetime.UTC).isoformat()));c.commit();c.close();return d
@app.put("/api/state/{student_id}")
def put_state(student_id:str,x:StateIn):
 c=con();c.execute("INSERT OR REPLACE INTO states VALUES(?,?,?,?)",(student_id,x.course_id,json.dumps(x.state),datetime.datetime.now(datetime.UTC).isoformat()));c.commit();c.close();return {"ok":True}
@app.get("/api/state/{student_id}")
def get_state(student_id:str,course_id:str):
 c=con();r=c.execute("SELECT state FROM states WHERE student_id=? AND course_id=?",(student_id,course_id)).fetchone();c.close();return {"state":json.loads(r["state"])} if r else {"state":None}
@app.post("/api/evidence")
def evidence(x:EventIn):
 c=con();c.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,correct,score,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,x.kind,x.ce,x.item_id,x.attempt,json.dumps(x.response,ensure_ascii=False),None if x.correct is None else int(x.correct),x.score,json.dumps(x.payload or {},ensure_ascii=False),datetime.datetime.now(datetime.UTC).isoformat()));c.commit();c.close();return {"ok":True}
@app.post("/api/result")
def result(x:ResultIn):
 c=con();c.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",(x.student_id,x.course_id,x.portfolio,x.exam,x.final,x.ce_passed,x.ce_total,int(x.ra_passed),json.dumps(x.recovery),datetime.datetime.now(datetime.UTC).isoformat()));c.commit();c.close();return {"ok":True}
@app.get("/api/teacher/overview")
def overview(x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();rows=[dict(r) for r in c.execute("SELECT * FROM results ORDER BY student_id")];c.close()
 for r in rows:r["recovery"]=json.loads(r["recovery"] or "[]")
 return rows
@app.get("/api/teacher/evidence/{student_id}")
def student_evidence(student_id:str,x_teacher_token:str|None=Header(None)):
 auth(x_teacher_token);c=con();rows=[dict(r) for r in c.execute("SELECT * FROM evidence WHERE student_id=? ORDER BY id",(student_id,))];c.close();return rows

import datetime
import json
import os,tempfile,importlib
os.environ["GRH_TEACHER_TOKEN"]="test-token"
fd,path=tempfile.mkstemp(suffix=".db");os.close(fd);os.environ["GRH_DB"]=path
import app as module
from fastapi.testclient import TestClient
client=TestClient(module.app)
H={"X-Teacher-Token":"test-token"}
TOKENS={}
def SH(student):
 if student not in TOKENS:
  r=client.post(f"/api/teacher/students/{student}",headers=H);assert r.status_code==200
  TOKENS[student]=r.json()["token"]
 return {"X-Student-Token":TOKENS[student]}
def start(kind,item="x",student="s1",course="GRH0652_UT1"):
 return client.post("/api/attempts/start",headers=SH(student),json={"student_id":student,"course_id":course,"kind":kind,"item_id":item,"payload":{}})
def submit(i,payload=None,student="s1"):return client.post(f"/api/attempts/{i}/submit",headers=SH(student),json={"payload":payload or {}})
def test_health():assert client.get("/health").json()["ok"]
def test_practice_three_attempt_limit():
 for n in range(3):
  r=start("practice","p1");assert r.status_code==200;assert r.json()["attempt"]==n+1;assert submit(r.json()["id"]).status_code==200
 assert start("practice","p1").status_code==409
def test_portfolio_two_attempt_limit():
 for n in range(2):
  r=start("portfolio","pf1");assert r.status_code==200;assert submit(r.json()["id"]).status_code==200
 assert start("portfolio","pf1").status_code==409
def test_exam_disabled_by_default():assert start("exam","final","exam0").status_code==403
def test_exam_one_attempt_and_resume():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/GRH0652_UT1",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"q1","ce":"1.a","q":"A","options":["Sí","No"],"answer":0},{"id":"q2","ce":"1.b","q":"B","options":["Sí","No"],"answer":1}]}
 assert client.put("/api/teacher/exam-bank/GRH0652_UT1",headers=H,json=bank).status_code==200
 body={"student_id":"exam1","course_id":"GRH0652_UT1","kind":"exam","item_id":"final","payload":{}}
 a=client.post("/api/exam/start",headers=SH("exam1"),json=body);assert a.status_code==200
 b=client.post("/api/exam/start",headers=SH("exam1"),json=body);assert b.status_code==200;assert b.json()["attempt_id"]==a.json()["attempt_id"];assert b.json()["questions"]==a.json()["questions"]
 answers={q["id"]:0 for q in a.json()["questions"]};done=client.post(f"/api/exam/{a.json()['attempt_id']}/submit",headers=SH("exam1"),json={"payload":{"answers":answers}});assert done.status_code==200
 assert client.post("/api/exam/start",headers=SH("exam1"),json=body).status_code==409
def test_config_weights_and_version():
 bad={"portfolio_weight":50,"exam_weight":60};assert client.put("/api/config/GRH0652_UT2",headers=H,json=bad).status_code==400
 good={"portfolio_weight":50,"exam_weight":50,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":False,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
 r=client.put("/api/config/GRH0652_UT2",headers=H,json=good);assert r.status_code==200;assert r.json()["version"]==1
def test_close_generates_only_failed_recovery():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/CLOSE",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"cq1","ce":"3.c","q":"C","options":[],"answer":True,"type":"tf"},{"id":"fq1","ce":"3.f","q":"F","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/CLOSE",headers=H,json=bank).status_code==200
 assert client.put("/api/teacher/portfolio-bank/CLOSE",headers=H,json={"items":[{"id":"pc","ce":"3.c","kind":"choice","prompt":"P","options":[],"answer":"x"},{"id":"pf","ce":"3.f","kind":"choice","prompt":"P","options":[],"answer":"x"}]}).status_code==200
 for student,score in (("fail",0),("pass",100)):
  for ce,item in (("3.c","pc"),("3.f","pf")):
   assert client.post("/api/evidence",headers=SH(student),json={"student_id":student,"course_id":"CLOSE","kind":"portfolio","ce":ce,"item_id":item,"attempt":1,"response":"x","correct":score==100,"score":score,"payload":{}}).status_code==200
  st=client.post("/api/exam/start",headers=SH(student),json={"student_id":student,"course_id":"CLOSE","kind":"exam","item_id":"final"});assert st.status_code==200,st.text
  ans={q["id"]:(True if score==100 else False) for q in st.json()["questions"]}
  assert client.post(f"/api/exam/{st.json()['attempt_id']}/submit",headers=SH(student),json={"payload":{"answers":ans}}).status_code==200
  forged={"student_id":student,"course_id":"CLOSE","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
  assert client.post("/api/result",headers=SH(student),json=forged).status_code==200
 r=client.post("/api/teacher/close/CLOSE",headers=H);assert r.status_code==200;assert r.json()["recovery_plans"]==1
 p=client.get("/api/recovery/fail/CLOSE",headers=SH("fail")).json()["plan"];assert p["criteria"]==["3.c","3.f"]
 assert client.get("/api/recovery/pass/CLOSE",headers=SH("pass")).json()["plan"] is None

def test_exam_snapshot_and_deadline_are_persisted():
    cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
    assert client.put("/api/config/GRH0652_UT4",headers=H,json=cfg).status_code==200
    bank={"questions":[{"id":"tq1","ce":"4.a","q":"A","options":["Sí","No"],"answer":0}]}
    assert client.put("/api/teacher/exam-bank/GRH0652_UT4",headers=H,json=bank).status_code==200
    r=client.post("/api/exam/start",headers=SH("timed"),json={"student_id":"timed","course_id":"GRH0652_UT4","kind":"exam","item_id":"final"})
    assert r.status_code==200
    data=r.json()
    assert data["version"] and data["deadline_at"]
    assert data["config"]["exam_minutes"]==45
    again=client.post("/api/exam/start",headers=SH("timed"),json={"student_id":"timed","course_id":"GRH0652_UT4","kind":"exam","item_id":"final"})
    assert again.status_code==200
    assert again.json()["version"]==data["version"]
    assert again.json()["deadline_at"]==data["deadline_at"]

def test_exam_supports_tf_and_multi_without_exposing_keys():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/TYPES",headers=H,json=cfg).status_code==200
 bank={"questions":[
  {"id":"c","ce":"x","q":"Choice","options":["A","B"],"answer":0,"type":"choice"},
  {"id":"t","ce":"x","q":"TF","options":[],"answer":True,"type":"tf"},
  {"id":"m","ce":"x","q":"Multi","options":["A","B","C"],"answer":[0,2],"type":"multi"}]}
 assert client.put("/api/teacher/exam-bank/TYPES",headers=H,json=bank).status_code==200
 r=client.post("/api/exam/start",headers=SH("typed"),json={"student_id":"typed","course_id":"TYPES","kind":"exam","item_id":"final"});assert r.status_code==200
 qs=r.json()["questions"];assert {q["type"] for q in qs}=={"choice","tf","multi"};assert all("answer" not in q for q in qs)

def test_missing_exam_bank_does_not_consume_attempt():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/ATOMIC",headers=H,json=cfg).status_code==200
 body={"student_id":"atomic","course_id":"ATOMIC","kind":"exam","item_id":"final","payload":{}}
 first=client.post("/api/exam/start",headers=SH("atomic"),json=body);assert first.status_code==409
 bank={"questions":[{"id":"a1","ce":"a","q":"A","options":["Sí","No"],"answer":0,"type":"choice"}]}
 assert client.put("/api/teacher/exam-bank/ATOMIC",headers=H,json=bank).status_code==200
 second=client.post("/api/exam/start",headers=SH("atomic"),json=body);assert second.status_code==200
 assert second.json()["attempt"]==1

def test_recovery_uses_configured_ce_threshold_and_closes_passed_plan():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":75,"exam_enabled":False,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/REC",headers=H,json=cfg).status_code==200
 c=module.con();c.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",("rec","REC",40,40,40,0,1,0,'["x"]',module.now()));c.commit();c.close()
 assert client.post("/api/teacher/close/REC",headers=H).status_code==200
 bank={"items":[
  {"id":"r1","ce":"x","kind":"choice","prompt":"A","options":["A","B"],"answer":0},
  {"id":"r2","ce":"x","kind":"tf","prompt":"B","options":[],"answer":True},
  {"id":"r3","ce":"x","kind":"multi","prompt":"C","options":["A","B","C"],"answer":[0,2]},
  {"id":"r4","ce":"x","kind":"free","prompt":"D","options":[],"answer":"Respuesta"}]}
 assert client.put("/api/teacher/recovery-bank/REC",headers=H,json=bank).status_code==200
 s=client.post("/api/recovery/start",headers=SH("rec"),json={"student_id":"rec","course_id":"REC","kind":"recovery","item_id":"ignored","payload":{}});assert s.status_code==200
 answers={"r1":0,"r2":True,"r3":[2,0],"r4":" respuesta "}
 done=client.post(f"/api/recovery/{s.json()['id']}/submit",headers=SH("rec"),json={"payload":{"answers":answers}});assert done.status_code==200, done.text
 assert done.json()["status"]=="passed"
 assert done.json()["result"]=={"ce_passed":1,"ce_total":1,"ra_passed":False,"recovery":[]}
 c=module.con();rr=c.execute("SELECT ce_passed,ce_total,ra_passed,recovery FROM results WHERE student_id=? AND course_id=?",("rec","REC")).fetchone();rp=c.execute("SELECT criteria,status FROM recovery_plans WHERE student_id=? AND course_id=?",("rec","REC")).fetchone();c.close()
 assert rr["ce_passed"]==1 and rr["ce_total"]==1 and rr["recovery"]=="[]"
 assert rp["criteria"]=="[]" and rp["status"]=="passed"
 assert client.post("/api/recovery/start",headers=SH("rec"),json={"student_id":"rec","course_id":"REC","kind":"recovery","item_id":"ignored","payload":{}}).status_code==409

def test_result_ignores_client_claims_and_recomputes_from_server_evidence():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/AUTH",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"q1","ce":"c1","q":"Q1","options":[],"answer":True,"type":"tf"},{"id":"q2","ce":"c2","q":"Q2","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/AUTH",headers=H,json=bank).status_code==200
 assert client.put("/api/teacher/portfolio-bank/AUTH",headers=H,json={"items":[{"id":"p1","ce":"c1","kind":"choice","prompt":"P","options":[],"answer":"x"},{"id":"p2","ce":"c2","kind":"choice","prompt":"P","options":[],"answer":"wrong"}]}).status_code==200
 for ce,item,score in [("c1","p1",100),("c2","p2",0)]:
  assert client.post("/api/evidence",headers=SH("auth"),json={"student_id":"auth","course_id":"AUTH","kind":"portfolio","ce":ce,"item_id":item,"attempt":1,"response":"x","correct":score==100,"score":score,"payload":{}}).status_code==200
 start=client.post("/api/exam/start",headers=SH("auth"),json={"student_id":"auth","course_id":"AUTH","kind":"exam","item_id":"final"});assert start.status_code==200,start.text
 qs=start.json()["questions"];answers={}
 for q in qs: answers[q["id"]]=True if q["ce"]=="c1" else False
 assert client.post(f"/api/exam/{start.json()['attempt_id']}/submit",headers=SH("auth"),json={"payload":{"answers":answers}}).status_code==200
 forged={"student_id":"auth","course_id":"AUTH","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
 r=client.post("/api/result",headers=SH("auth"),json=forged);assert r.status_code==200,r.text
 d=r.json();assert d["final"]==50.0;assert d["ce_passed"]==1;assert d["ra_passed"] is False;assert d["recovery"]==["c2"]

def test_missing_ce_cannot_disappear_from_authoritative_denominator():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/UNIVERSE",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"u1","ce":"c1","q":"Q1","options":[],"answer":True,"type":"tf"},{"id":"u2","ce":"c2","q":"Q2","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/UNIVERSE",headers=H,json=bank).status_code==200
 assert client.put("/api/teacher/portfolio-bank/UNIVERSE",headers=H,json={"items":[{"id":"p1","ce":"c1","kind":"choice","prompt":"P","options":[],"answer":"x"}]}).status_code==200
 assert client.post("/api/evidence",headers=SH("u"),json={"student_id":"u","course_id":"UNIVERSE","kind":"portfolio","ce":"c1","item_id":"p1","attempt":1,"response":"x","correct":True,"score":100,"payload":{}}).status_code==200
 st=client.post("/api/exam/start",headers=SH("u"),json={"student_id":"u","course_id":"UNIVERSE","kind":"exam","item_id":"final"});assert st.status_code==200
 answers={q["id"]:(True if q["ce"]=="c1" else False) for q in st.json()["questions"]}
 assert client.post(f"/api/exam/{st.json()['attempt_id']}/submit",headers=SH("u"),json={"payload":{"answers":answers}}).status_code==200
 forged={"student_id":"u","course_id":"UNIVERSE","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
 r=client.post("/api/result",headers=SH("u"),json=forged);assert r.status_code==200,r.text
 d=r.json();assert d["ce_total"]==2;assert d["ce"]["c2"]["portfolio"]==0;assert d["ce"]["c2"]["passed"] is False;assert "c2" in d["recovery"]

def test_portfolio_score_is_server_authoritative():
 bank={"items":[{"id":"p1","ce":"c1","kind":"choice","prompt":"P","options":["A","B"],"answer":1}]}
 assert client.put("/api/teacher/portfolio-bank/PORT",headers=H,json=bank).status_code==200
 forged={"student_id":"s","course_id":"PORT","kind":"portfolio","ce":"c1","item_id":"p1","attempt":1,"response":0,"correct":True,"score":100,"payload":{}}
 r=client.post("/api/evidence",headers=SH(forged["student_id"]),json=forged);assert r.status_code==200,r.text
 assert r.json()["correct"] is False and r.json()["score"]==0
 c=module.con();row=c.execute("SELECT correct,score FROM evidence WHERE student_id='s' AND course_id='PORT' AND item_id='p1'").fetchone();c.close()
 assert row["correct"]==0 and row["score"]==0
 forged["response"]=1;forged["correct"]=False;forged["score"]=0;forged["attempt"]=2
 r=client.post("/api/evidence",headers=SH(forged["student_id"]),json=forged);assert r.status_code==200
 assert r.json()["correct"] is True and r.json()["score"]==100


def test_portfolio_match_normalizes_browser_string_indices():
 bank={"items":[{"id":"m1","ce":"c1","kind":"match","prompt":"Relaciona","options":[],"answer":[0,1,2]}]}
 assert client.put("/api/teacher/portfolio-bank/MATCH",headers=H,json=bank).status_code==200
 body={"student_id":"match-student","course_id":"MATCH","kind":"portfolio","ce":"c1","item_id":"m1","attempt":1,"response":["0","1","2"],"correct":False,"score":0,"payload":{}}
 r=client.post("/api/evidence",headers=SH("match-student"),json=body)
 assert r.status_code==200,r.text
 assert r.json()["correct"] is True and r.json()["score"]==100
 body["attempt"]=2;body["response"]=["0","2","1"]
 r=client.post("/api/evidence",headers=SH("match-student"),json=body)
 assert r.status_code==200,r.text
 assert r.json()["correct"] is False and r.json()["score"]==0


def test_public_portfolio_files_contain_no_evaluable_keys():
 from pathlib import Path
 import json
 bank_dir=Path(module.__file__).resolve().parent/"banks"
 total=0
 for unit in ("ut1","ut2","ut3","ut4"):
  data=json.loads((bank_dir/f"{unit}_portfolio.json").read_text(encoding="utf-8"))
  for item in data["items"]:
   total+=1
   assert "answer" not in item
   assert "feedback" not in item
 assert total==198


def test_private_portfolio_keys_are_provisioned_only_through_teacher_api():
 db=module.con();db.execute("DELETE FROM portfolio_banks WHERE course_id='PRIVATE'");db.commit();db.close()
 bank={"items":[{"id":"secret1","ce":"1.a","kind":"choice","prompt":"P","options":["A","B"],"answer":1}]}
 assert client.put("/api/teacher/portfolio-bank/PRIVATE",json=bank).status_code==401
 assert client.put("/api/teacher/portfolio-bank/PRIVATE",headers=H,json=bank).status_code==200
 db=module.con();row=db.execute("SELECT answer FROM portfolio_banks WHERE course_id='PRIVATE' AND item_id='secret1'").fetchone();db.close()
 assert row is not None and row["answer"]=="1"


def _public_portfolio_metadata():
 from pathlib import Path
 import json
 bank_dir=Path(module.__file__).resolve().parent/"banks";items=[]
 for unit in ("ut1","ut2","ut3","ut4"):
  items.extend(json.loads((bank_dir/f"{unit}_portfolio.json").read_text(encoding="utf-8"))["items"])
 return items

def _private_keys(items):
 def dummy(q):
  kind=q["kind"]
  if kind=="multi":return []
  if kind in ("order","match"):return []
  if kind=="tf":return True
  if kind=="choice":return 0
  return "respuesta"
 return [{"id":q["id"],"ce":q["ce"],"kind":q["kind"],"answer":dummy(q)} for q in items]

def test_private_key_provisioning_requires_teacher_and_exact_198():
 public=_public_portfolio_metadata();keys=_private_keys(public)
 assert len(keys)==198
 assert client.put("/api/teacher/portfolio-keys/GRH0652",json={"items":keys}).status_code==401
 r=client.put("/api/teacher/portfolio-keys/GRH0652",headers=H,json={"items":keys[:-1]})
 assert r.status_code==400
 r=client.put("/api/teacher/portfolio-keys/GRH0652",headers=H,json={"items":keys})
 assert r.status_code==200 and r.json()["items"]==198
 db=module.con();n=db.execute("SELECT COUNT(*) n FROM portfolio_banks WHERE course_id='GRH0652'").fetchone()["n"];db.close()
 assert n==198

def test_private_key_provisioning_rejects_metadata_tampering_and_rolls_back():
 public=_public_portfolio_metadata();keys=_private_keys(public)
 assert client.put("/api/teacher/portfolio-keys/GRH0652",headers=H,json={"items":keys}).status_code==200
 db=module.con();before=db.execute("SELECT item_id,ce,kind,answer FROM portfolio_banks WHERE course_id='GRH0652' ORDER BY item_id").fetchall();before=[tuple(x) for x in before];db.close()
 bad=[dict(x) for x in keys];bad[0]["ce"]="9.z"
 r=client.put("/api/teacher/portfolio-keys/GRH0652",headers=H,json={"items":bad})
 assert r.status_code==400
 db=module.con();after=db.execute("SELECT item_id,ce,kind,answer FROM portfolio_banks WHERE course_id='GRH0652' ORDER BY item_id").fetchall();after=[tuple(x) for x in after];db.close()
 assert after==before


def test_ai_settings_are_teacher_only_and_key_is_never_returned():
 body={"enabled":True,"base_url":"https://ai.example/v1","api_key":"secret-key","model":"test-model","rubric":"Acepta equivalentes","confidence":0.8,"auto_kinds":["free"]}
 assert client.put("/api/teacher/ai-settings",json=body).status_code==401
 r=client.put("/api/teacher/ai-settings",headers=H,json=body);assert r.status_code==200,r.text
 d=r.json();assert d["enabled"] is True and d["api_key_set"] is True and "api_key" not in d
 g=client.get("/api/teacher/ai-settings",headers=H);assert g.status_code==200 and "api_key" not in g.json()

def test_ai_free_grading_accepts_semantic_result_and_records_review(monkeypatch):
 body={"enabled":True,"base_url":"https://ai.example/v1","api_key":"secret-key","model":"test-model","rubric":"R","confidence":0.75,"auto_kinds":["free"]}
 assert client.put("/api/teacher/ai-settings",headers=H,json=body).status_code==200
 bank={"items":[{"id":"free1","ce":"1.a","kind":"free","prompt":"Define","options":[],"answer":"Contrato laboral"}]}
 assert client.put("/api/teacher/portfolio-bank/AI",headers=H,json=bank).status_code==200
 monkeypatch.setattr(module,"ai_grade",lambda *a,**k:{"score":90,"confidence":0.95,"verdict":"correct","feedback":"Equivalente correcto"})
 ev={"student_id":"ai-student","course_id":"AI","kind":"portfolio","ce":"1.a","item_id":"free1","attempt":1,"response":"Acuerdo de trabajo entre empresa y trabajador","correct":False,"score":0,"payload":{}}
 r=client.post("/api/evidence",headers=SH("ai-student"),json=ev);assert r.status_code==200,r.text
 assert r.json()["score"]==90 and r.json()["correct"] is True
 rows=client.get("/api/teacher/ai-reviews?course_id=AI",headers=H).json();assert rows[0]["status"]=="accepted" and "reference" not in rows[0]

def test_low_confidence_ai_answer_is_not_auto_scored(monkeypatch):
 monkeypatch.setattr(module,"ai_grade",lambda *a,**k:{"score":70,"confidence":0.3,"verdict":"partial","feedback":"Revisión necesaria"})
 ev={"student_id":"ai-low","course_id":"AI","kind":"portfolio","ce":"1.a","item_id":"free1","attempt":1,"response":"Respuesta dudosa","payload":{}}
 r=client.post("/api/evidence",headers=SH("ai-low"),json=ev);assert r.status_code==200,r.text
 assert r.json()["score"] is None and r.json()["correct"] is None
 rows=client.get("/api/teacher/ai-reviews?course_id=AI",headers=H).json();assert any(x["student_id"]=="ai-low" and x["status"]=="pending" for x in rows)


def test_teacher_can_override_pending_ai_review_authoritatively(monkeypatch):
 body={"enabled":True,"base_url":"https://ai.example/v1","api_key":"secret-key","model":"test-model","rubric":"R","confidence":0.9,"auto_kinds":["free"]}
 assert client.put("/api/teacher/ai-settings",headers=H,json=body).status_code==200
 bank={"items":[{"id":"rev1","ce":"1.b","kind":"free","prompt":"Razona","options":[],"answer":"Referencia"}]}
 assert client.put("/api/teacher/portfolio-bank/REVIEW",headers=H,json=bank).status_code==200
 monkeypatch.setattr(module,"ai_grade",lambda *a,**k:{"score":65,"confidence":0.4,"verdict":"partial","feedback":"Dudosa"})
 ev={"student_id":"review-student","course_id":"REVIEW","kind":"portfolio","ce":"1.b","item_id":"rev1","attempt":1,"response":"Respuesta alternativa","payload":{}}
 r=client.post("/api/evidence",headers=SH("review-student"),json=ev);assert r.status_code==200 and r.json()["score"] is None
 reviews=client.get("/api/teacher/ai-reviews?course_id=REVIEW",headers=H).json();rid=reviews[0]["id"]
 done=client.put(f"/api/teacher/ai-reviews/{rid}",headers=H,json={"score":82,"feedback":"Respuesta válida y bien razonada","status":"accepted"});assert done.status_code==200,done.text
 assert done.json()["score"]==82 and done.json()["correct"] is True
 db=module.con();row=db.execute("SELECT score,correct,payload FROM evidence WHERE student_id='review-student' AND course_id='REVIEW' AND item_id='rev1'").fetchone();db.close()
 assert row["score"]==82 and row["correct"]==1 and "Respuesta válida" in row["payload"]


def test_ai_rubric_hierarchy_item_over_ce_over_general():
 course="RUB";ce="4.f";item="nomina-1"
 assert client.put("/api/teacher/ai-rubrics",headers=H,json={"course_id":course,"name":"Curso","rubric":"general"}).status_code==200
 assert client.put("/api/teacher/ai-rubrics",headers=H,json={"course_id":course,"ce":ce,"name":"CE","rubric":"criterio"}).status_code==200
 assert client.put("/api/teacher/ai-rubrics",headers=H,json={"course_id":course,"ce":ce,"item_id":item,"name":"Actividad","rubric":"actividad"}).status_code==200
 db=module.con();assert module.rubric_for(db,course,ce,item,"fallback")["rubric"]=="actividad";assert module.rubric_for(db,course,ce,"otra","fallback")["rubric"]=="criterio";assert module.rubric_for(db,course,"4.a","otra","fallback")["rubric"]=="general";db.close()
 rows=client.get("/api/teacher/ai-rubrics?course_id=RUB",headers=H);assert rows.status_code==200 and len(rows.json())==3
 rid=next(x["id"] for x in rows.json() if x["item_id"]==item);assert client.delete(f"/api/teacher/ai-rubrics/{rid}",headers=H).status_code==200


def test_analytic_rubric_requires_100_percent_and_calculates_weighted_score(monkeypatch):
 bad={"course_id":"ANA","ce":"4.f","name":"Nómina","criteria":[{"id":"a","name":"Bases","weight":60},{"id":"b","name":"Cuotas","weight":30}]}
 assert client.put("/api/teacher/ai-rubrics",headers=H,json=bad).status_code==400
 good={"course_id":"ANA","ce":"4.f","name":"Nómina","rubric":"Revisar cálculo y coherencia","criteria":[{"id":"a","name":"Bases","weight":60,"description":"Bases correctas"},{"id":"b","name":"Cuotas","weight":40,"description":"Cuotas correctas"}]}
 r=client.put("/api/teacher/ai-rubrics",headers=H,json=good);assert r.status_code==200,r.text
 settings={"base_url":"https://x/v1","api_key":"k","model":"m","rubric":"R","criteria":good["criteria"]}
 class Resp:
  def raise_for_status(self):pass
  def json(self):return {"choices":[{"message":{"content":json.dumps({"score":1,"confidence":.9,"verdict":"partial","feedback":"F","criteria":[{"id":"a","score":100,"feedback":"ok"},{"id":"b","score":50,"feedback":"parcial"}]})}}]}
 class Dummy:
  def __init__(self,*a,**k):pass
  def __enter__(self):return self
  def __exit__(self,*a):pass
  def post(self,*a,**k):return Resp()
 monkeypatch.setattr(module.httpx,"Client",Dummy);g=module.ai_grade(settings,"respuesta","referencia",{})
 assert g["score"]==80 and len(g["criteria"])==2 and g["criteria"][0]["weight"]==60


def test_student_feedback_is_private_and_hides_reference():
 db=module.con();db.execute("INSERT INTO ai_reviews(student_id,course_id,ce,item_id,attempt,response,reference,score,confidence,verdict,feedback,status,created_at,breakdown) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("fb-student","FB","4.f","n1",1,'"respuesta"','"SECRETO"',80,.9,"correct","Buen trabajo","accepted",module.now(),json.dumps([{"id":"a","name":"Bases","weight":60,"score":90,"feedback":"Bien"},{"id":"b","name":"Cuotas","weight":40,"score":65,"feedback":"Revisar"}])));db.commit();db.close()
 client.post("/api/teacher/students/fb-student",headers=H)
 # Replace generated token with one we can retrieve only for this test by direct DB read.
 db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='fb-student'").fetchone()["token"];db.close()
 r=client.get("/api/student/feedback/FB",headers={"X-Student-Token":tok});assert r.status_code==200,r.text
 d=r.json()[0];assert d["score"]==80 and len(d["breakdown"])==2 and "reference" not in d and "response" not in d
 assert client.get("/api/student/feedback/FB").status_code==401


def test_teacher_grade_adjustment_is_audited_without_destroying_original_result():
 db=module.con();db.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",("audit-student","AUDIT",70,60,64,2,3,0,json.dumps(["1.c"]),module.now()));db.commit();db.close()
 r=client.post("/api/teacher/grade-adjustment/AUDIT/audit-student",headers=H,json={"scope":"ra","new_score":68,"reason":"Revisión docente motivada"});assert r.status_code==200,r.text;assert r.json()["old_score"]==64 and r.json()["official"] is True
 rec=client.get("/api/teacher/student-record/AUDIT/audit-student",headers=H);assert rec.status_code==200;d=rec.json();assert d["result"]["calculated"]["final"]==64 and d["result"]["final"]==68 and d["adjustments"][0]["new_score"]==68 and d["adjustments"][0]["active"]==1
 aid=d["adjustments"][0]["id"];rev=client.post(f"/api/teacher/grade-adjustment/{aid}/reverse",headers=H,json={"reason":"Se restaura el cálculo automático"});assert rev.status_code==200,rev.text
 d2=client.get("/api/teacher/student-record/AUDIT/audit-student",headers=H).json();assert d2["result"]["final"]==64 and d2["adjustments"][0]["active"]==0 and d2["adjustments"][0]["reversal_reason"]=="Se restaura el cálculo automático"
 assert client.post("/api/teacher/grade-adjustment/AUDIT/audit-student",headers=H,json={"scope":"ra","new_score":101,"reason":"Motivo válido"}).status_code==400
 assert client.post("/api/teacher/grade-adjustment/AUDIT/audit-student",headers=H,json={"scope":"ra","new_score":68,"reason":"x"}).status_code==400


def test_evidence_adjustment_recomputes_ce_ra_and_recovery_and_is_reversible():
 db=module.con();db.execute("INSERT OR REPLACE INTO configs(course_id,config,version,updated_at) VALUES(?,?,?,?)",("REC",json.dumps({**module.DEFAULT,"portfolio_weight":100,"exam_weight":0,"ce_pass_percent":100}),1,module.now()));db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("REC","q1","1.a","q","[]",'"a"',"choice"));db.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,correct,score,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",("rec-student","REC","portfolio","1.a","p1",1,'"x"',0,40,"{}",module.now()));eid=db.execute("SELECT last_insert_rowid() id").fetchone()["id"];db.execute("INSERT OR REPLACE INTO results VALUES(?,?,?,?,?,?,?,?,?,?)",("rec-student","REC",40,0,40,0,1,0,json.dumps(["1.a"]),module.now()));db.execute("INSERT OR REPLACE INTO recovery_plans VALUES(?,?,?,?,?)",("rec-student","REC",json.dumps(["1.a"]),"pending",module.now()));db.commit();db.close()
 r=client.post("/api/teacher/grade-adjustment/REC/rec-student",headers=H,json={"scope":"evidence","scope_key":str(eid),"new_score":80,"reason":"Corrección manual revisada"});assert r.status_code==200,r.text;assert r.json()["result"]["final"]==80 and r.json()["result"]["ra_passed"] is True and r.json()["result"]["recovery"]==[]
 rec=client.get("/api/teacher/student-record/REC/rec-student",headers=H).json();aid=next(x["id"] for x in rec["adjustments"] if x["active"])
 rr=client.post(f"/api/teacher/grade-adjustment/{aid}/reverse",headers=H,json={"reason":"Se recupera la corrección automática"});assert rr.status_code==200,rr.text;assert rr.json()["result"]["final"]==40 and rr.json()["result"]["ra_passed"] is False and rr.json()["result"]["recovery"]==["1.a"]


def test_exam_integrity_is_persisted_with_authoritative_submission():
 db=module.con();db.execute("INSERT OR REPLACE INTO configs(course_id,config,version,updated_at) VALUES(?,?,?,?)",("INT",json.dumps({**module.DEFAULT,"exam_enabled":True,"exam_questions_per_ce":1}),1,module.now()));db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("INT","iq1","1.a","Pregunta",json.dumps(["A","B"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/int-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='int-student'").fetchone()["token"];db.close();sh={"X-Student-Token":tok};st=client.post("/api/exam/start",headers=sh,json={"student_id":"int-student","course_id":"INT","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;q=st.json()["questions"][0];sub=client.post(f"/api/exam/{st.json()['attempt_id']}/submit",headers=sh,json={"payload":{"answers":{q["id"]:0},"integrity":{"incidents":2,"auto":True,"incident_log":[{"reason":"tab_hidden","at":"2026-09-26T10:00:00+00:00"},{"reason":"fullscreen_exit","at":"2026-09-26T10:01:00+00:00"}]}}});assert sub.status_code==200,sub.text;rec=client.get("/api/teacher/student-record/INT/int-student",headers=H).json();ex=next(x for x in rec["attempts"] if x["kind"]=="exam");assert ex["payload"]["integrity"]["incidents"]==2 and ex["payload"]["integrity"]["auto"] is True and len(ex["payload"]["integrity"]["incident_log"])==2


def test_exam_integrity_configuration_and_student_exception():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":35,"exam_integrity_enabled":True,"exam_fullscreen_required":True,"exam_incident_limit":2,"exam_incident_policy":"warn","exam_exempt_students":["exempt-student"]};r=client.put("/api/config/SECURE",headers=H,json=body);assert r.status_code==200,r.text
 db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("SECURE","sq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/exempt-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='exempt-student'").fetchone()["token"];db.close();st=client.post("/api/exam/start",headers={"X-Student-Token":tok},json={"student_id":"exempt-student","course_id":"SECURE","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;cfg=st.json()["config"];assert cfg["exam_minutes"]==35 and cfg["exam_incident_limit"]==2 and cfg["exam_incident_policy"]=="warn" and cfg["exam_integrity_exempt"] is True
 bad={**body,"exam_incident_policy":"invalid"};assert client.put("/api/config/BAD",headers=H,json=bad).status_code==400


def test_exam_call_window_pin_allowlist_and_immediate_close():
 body={**module.DEFAULT,"exam_enabled":True,"exam_open_at":"","exam_close_at":"","exam_pin":"2468","exam_allowed_students":["call-student"]};assert client.put("/api/config/CALL",headers=H,json=body).status_code==200
 db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("CALL","cq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/call-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='call-student'").fetchone()["token"];db.close();sh={"X-Student-Token":tok}
 bad=client.post("/api/exam/start",headers=sh,json={"student_id":"call-student","course_id":"CALL","kind":"exam","item_id":"final","pin":"0000","payload":{}});assert bad.status_code==403
 ok=client.post("/api/exam/start",headers=sh,json={"student_id":"call-student","course_id":"CALL","kind":"exam","item_id":"final","pin":"2468","payload":{}});assert ok.status_code==200,ok.text;assert ok.json()["config"]["exam_pin_required"] is True and "exam_pin" not in ok.json()["config"]
 cl=client.post("/api/teacher/exam-close/CALL",headers=H);assert cl.status_code==200;client.post("/api/teacher/students/call-student-2",headers=H);db=module.con();tok2=db.execute("SELECT token FROM students WHERE student_id='call-student-2'").fetchone()["token"];db.close();den=client.post("/api/exam/start",headers={"X-Student-Token":tok2},json={"student_id":"call-student-2","course_id":"CALL","kind":"exam","item_id":"final","pin":"2468","payload":{}});assert den.status_code==403


def test_teacher_live_exam_monitor_and_individual_finish():
 body={**module.DEFAULT,"exam_enabled":True};assert client.put("/api/config/MON",headers=H,json=body).status_code==200;db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("MON","mq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/monitor-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='monitor-student'").fetchone()["token"];db.close();st=client.post("/api/exam/start",headers={"X-Student-Token":tok},json={"student_id":"monitor-student","course_id":"MON","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;aid=st.json()["attempt_id"];m=client.get("/api/teacher/exam-monitor/MON",headers=H);assert m.status_code==200;row=next(x for x in m.json()["attempts"] if x["attempt_id"]==aid);assert row["status"]=="started" and row["remaining_seconds"] is not None
 fin=client.post(f"/api/teacher/exam-monitor/{aid}/finish",headers=H);assert fin.status_code==200;assert fin.json()["status"]=="teacher_finished";m2=client.get("/api/teacher/exam-monitor/MON",headers=H).json();assert next(x for x in m2["attempts"] if x["attempt_id"]==aid)["status"]=="teacher_finished"


def test_teacher_can_extend_only_one_active_exam():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":20};assert client.put("/api/config/EXT",headers=H,json=body).status_code==200;db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("EXT","eq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/ext-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='ext-student'").fetchone()["token"];db.close();st=client.post("/api/exam/start",headers={"X-Student-Token":tok},json={"student_id":"ext-student","course_id":"EXT","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;aid=st.json()["attempt_id"];old=st.json()["deadline_at"];ex=client.post(f"/api/teacher/exam-monitor/{aid}/extend",headers=H,json={"minutes":15,"reason":"Adaptación temporal"});assert ex.status_code==200,ex.text;assert datetime.datetime.fromisoformat(ex.json()["deadline_at"])>datetime.datetime.fromisoformat(old);mon=client.get("/api/teacher/exam-monitor/EXT",headers=H).json();assert mon["summary"]["active"]>=1;row=next(x for x in mon["attempts"] if x["attempt_id"]==aid);assert row["remaining_seconds"]>20*60


def test_student_live_exam_status_reflects_extension_and_teacher_finish():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":25};assert client.put("/api/config/LIVE",headers=H,json=body).status_code==200;db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("LIVE","lq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/live-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='live-student'").fetchone()["token"];db.close();sh={"X-Student-Token":tok};st=client.post("/api/exam/start",headers=sh,json={"student_id":"live-student","course_id":"LIVE","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;aid=st.json()["attempt_id"];s1=client.get(f"/api/exam/{aid}/status",headers=sh);assert s1.status_code==200 and s1.json()["status"]=="started";ex=client.post(f"/api/teacher/exam-monitor/{aid}/extend",headers=H,json={"minutes":12,"reason":"Incidencia técnica"});assert ex.status_code==200;s2=client.get(f"/api/exam/{aid}/status",headers=sh).json();assert len(s2["time_extensions"])==1 and s2["time_extensions"][0]["minutes"]==12;assert client.post(f"/api/teacher/exam-monitor/{aid}/finish",headers=H).status_code==200;s3=client.get(f"/api/exam/{aid}/status",headers=sh).json();assert s3["status"]=="teacher_finished" and s3["teacher_finished"] is True


def test_exam_draft_autosave_and_resume_same_attempt():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":30};assert client.put("/api/config/DRAFT",headers=H,json=body).status_code==200;db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("DRAFT","dq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/draft-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='draft-student'").fetchone()["token"];db.close();sh={"X-Student-Token":tok};payload={"student_id":"draft-student","course_id":"DRAFT","kind":"exam","item_id":"final","payload":{}};st=client.post("/api/exam/start",headers=sh,json=payload);assert st.status_code==200,st.text;aid=st.json()["attempt_id"];qid=st.json()["questions"][0]["id"];sv=client.put(f"/api/exam/{aid}/answers",headers=sh,json={"payload":{"answers":{qid:0}}});assert sv.status_code==200 and sv.json()["count"]==1;rs=client.post("/api/exam/start",headers=sh,json=payload);assert rs.status_code==200,rs.text;assert rs.json()["resumed"] is True and rs.json()["attempt_id"]==aid and rs.json()["saved_answers"][qid]==0


def test_timeout_auto_submit_has_short_grace_but_manual_late_submit_is_rejected():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":30};assert client.put("/api/config/TIMEOUT",headers=H,json=body).status_code==200;db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("TIMEOUT","tq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close()
 def start(sid):
  client.post(f"/api/teacher/students/{sid}",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id=?",(sid,)).fetchone()["token"];db.close();sh={"X-Student-Token":tok};st=client.post("/api/exam/start",headers=sh,json={"student_id":sid,"course_id":"TIMEOUT","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;return sh,st.json()
 sh,st=start("timeout-auto");aid=st["attempt_id"];qid=st["questions"][0]["id"];db=module.con();db.execute("UPDATE exam_versions SET deadline_at=? WHERE attempt_id=?",((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=2)).isoformat(),aid));db.commit();db.close();r=client.post(f"/api/exam/{aid}/submit",headers=sh,json={"payload":{"answers":{qid:0},"integrity":{"auto":True,"reason":"timeout"}}});assert r.status_code==200,r.text
 sh2,st2=start("timeout-manual");aid2=st2["attempt_id"];qid2=st2["questions"][0]["id"];db=module.con();db.execute("UPDATE exam_versions SET deadline_at=? WHERE attempt_id=?",((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(seconds=2)).isoformat(),aid2));db.commit();db.close();r2=client.post(f"/api/exam/{aid2}/submit",headers=sh2,json={"payload":{"answers":{qid2:0},"integrity":{"auto":False}}});assert r2.status_code==410


def test_student_teacher_and_record_share_same_official_engine_after_evidence_adjustment():
 body={**module.DEFAULT,"portfolio_weight":100,"exam_weight":0,"ce_pass_percent":100};assert client.put("/api/config/ONEENGINE",headers=H,json=body).status_code==200;client.post("/api/teacher/students/engine-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='engine-student'").fetchone()["token"];db.execute("INSERT OR REPLACE INTO portfolio_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("ONEENGINE","p1","1.a","choice",json.dumps("A")));db.commit();db.close();sh={"X-Student-Token":tok};ev=client.post("/api/evidence",headers=sh,json={"student_id":"engine-student","course_id":"ONEENGINE","kind":"portfolio","ce":"1.a","item_id":"p1","attempt":1,"response":"B"});assert ev.status_code==200,ev.text;db=module.con();eid=db.execute("SELECT id FROM evidence WHERE student_id='engine-student' AND course_id='ONEENGINE' ORDER BY id DESC LIMIT 1").fetchone()["id"];db.close();adj=client.post("/api/teacher/grade-adjustment/ONEENGINE/engine-student",headers=H,json={"scope":"evidence","scope_key":str(eid),"new_score":80,"reason":"Corrección docente"});assert adj.status_code==200,adj.text;sd=client.get("/api/student/dashboard/ONEENGINE",headers=sh).json();td=client.get("/api/teacher/dashboard/ONEENGINE",headers=H).json();rd=client.get("/api/teacher/student-record/ONEENGINE/engine-student",headers=H).json();tr=next(x for x in td["students"] if x["student_id"]=="engine-student");assert sd["result"]["final"]==tr["result"]["final"]==rd["result"]["final"]==80;assert sd["ce"]["1.a"]["final"]==tr["ce"]["1.a"]["final"]==rd["result"]["ce"]["1.a"]["final"]==80


def test_teacher_ai_decision_recomputes_official_ce_ra_and_recovery():
 body={**module.DEFAULT,"portfolio_weight":100,"exam_weight":0,"ce_pass_percent":100};assert client.put("/api/config/AIRECALC",headers=H,json=body).status_code==200;client.post("/api/teacher/students/ai-recalc",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='ai-recalc'").fetchone()["token"];db.execute("INSERT OR REPLACE INTO portfolio_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("AIRECALC","free1","1.a","free",json.dumps("respuesta modelo")));db.execute("INSERT INTO evidence(student_id,course_id,kind,ce,item_id,attempt,response,correct,score,payload,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",("ai-recalc","AIRECALC","portfolio","1.a","free1",1,json.dumps("respuesta alumno"),None,None,json.dumps({}),module.now()));eid=db.execute("SELECT last_insert_rowid() id").fetchone()["id"];db.execute("INSERT INTO ai_reviews(student_id,course_id,ce,item_id,attempt,response,reference,score,confidence,verdict,feedback,status,created_at,breakdown) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",("ai-recalc","AIRECALC","1.a","free1",1,json.dumps("respuesta alumno"),json.dumps("respuesta modelo"),40,0.5,"partial","Pendiente","pending",module.now(),"[]"));rid=db.execute("SELECT last_insert_rowid() id").fetchone()["id"];db.commit();db.close();r=client.put(f"/api/teacher/ai-reviews/{rid}",headers=H,json={"score":80,"feedback":"Corrección docente","status":"accepted"});assert r.status_code==200,r.text;z=r.json();assert z["evidence_id"]==eid and z["result"]["ce"]["1.a"]["final"]==80 and z["result"]["ra_passed"] is True and z["result"]["recovery"]==[];sd=client.get("/api/student/dashboard/AIRECALC",headers={"X-Student-Token":tok}).json();assert sd["result"]["final"]==80 and sd["result"]["ra_passed"] is True


def test_semantic_kinds_use_ai_only_when_enabled_and_objective_kinds_stay_deterministic(monkeypatch):
 body={**module.DEFAULT};assert client.put("/api/config/SEMANTIC",headers=H,json=body).status_code==200;client.post("/api/teacher/students/semantic-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='semantic-student'").fetchone()["token"];db.execute("INSERT OR REPLACE INTO portfolio_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("SEMANTIC","case1","1.a","case",json.dumps("Solución razonada")));db.execute("INSERT OR REPLACE INTO portfolio_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("SEMANTIC","choice1","1.a","choice",json.dumps("A")));db.commit();db.close();sh={"X-Student-Token":tok};called=[]
 def fake(settings,response,reference,context):
  called.append(context["kind"]);return {"score":82.0,"confidence":.95,"verdict":"correct","feedback":"Equivalente","criteria":[]}
 monkeypatch.setattr(module,"ai_grade",fake);db=module.con();db.execute("INSERT OR REPLACE INTO ai_settings(id,enabled,base_url,api_key,model,rubric,confidence,auto_kinds,updated_at) VALUES(1,1,'x','k','m','r',.75,?,?)",(json.dumps(["case","calculation","text","free"]),module.now()));db.commit();db.close();r=client.post("/api/evidence",headers=sh,json={"student_id":"semantic-student","course_id":"SEMANTIC","kind":"portfolio","ce":"1.a","item_id":"case1","attempt":1,"response":"Otra formulación correcta"});assert r.status_code==200,r.text;assert r.json()["score"]==82 and called==["case"];r2=client.post("/api/evidence",headers=sh,json={"student_id":"semantic-student","course_id":"SEMANTIC","kind":"portfolio","ce":"1.a","item_id":"choice1","attempt":1,"response":"B"});assert r2.status_code==200 and r2.json()["score"]==0 and called==["case"]


def test_recovery_semantic_case_uses_ai_and_low_confidence_stays_review(monkeypatch):
 body={**module.DEFAULT};assert client.put("/api/config/RECAI",headers=H,json=body).status_code==200;client.post("/api/teacher/students/rec-ai",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='rec-ai'").fetchone()["token"];db.execute("INSERT OR REPLACE INTO recovery_plans VALUES(?,?,?,?,?)",("rec-ai","RECAI",json.dumps(["1.a"]),"pending",module.now()));db.execute("INSERT OR REPLACE INTO recovery_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("RECAI","rcase","1.a","case",json.dumps("solución modelo")));db.execute("INSERT OR REPLACE INTO ai_settings(id,enabled,base_url,api_key,model,rubric,confidence,auto_kinds,updated_at) VALUES(1,1,'x','k','m','r',.75,?,?)",(json.dumps(["case"]),module.now()));db.commit();db.close()
 def fake(settings,response,reference,context):return {"score":70.0,"confidence":.50,"verdict":"partial","feedback":"Revisar","criteria":[]}
 monkeypatch.setattr(module,"ai_grade",fake);sh={"X-Student-Token":tok};st=client.post("/api/recovery/start",headers=sh,json={"student_id":"rec-ai","course_id":"RECAI","kind":"recovery","item_id":"recovery-final","payload":{}});assert st.status_code==200,st.text;aid=st.json()["id"];r=client.post(f"/api/recovery/{aid}/submit",headers=sh,json={"payload":{"answers":{"rcase":"respuesta razonada"}}});assert r.status_code==200,r.text;z=r.json();assert z["status"]=="review" and z["criteria_passed"]==[];db=module.con();rv=db.execute("SELECT status,score FROM ai_reviews WHERE student_id='rec-ai' AND course_id='RECAI' ORDER BY id DESC LIMIT 1").fetchone();db.close();assert rv["status"]=="pending" and rv["score"]==70


def test_teacher_decision_on_recovery_ai_review_updates_recovery_and_official_result(monkeypatch):
 body={**module.DEFAULT,"portfolio_weight":100,"exam_weight":0,"ce_pass_percent":100};assert client.put("/api/config/REVIEWREC",headers=H,json=body).status_code==200;client.post("/api/teacher/students/review-rec",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='review-rec'").fetchone()["token"];db.execute("INSERT OR REPLACE INTO recovery_plans VALUES(?,?,?,?,?)",("review-rec","REVIEWREC",json.dumps(["1.a"]),"pending",module.now()));db.execute("INSERT OR REPLACE INTO recovery_banks(course_id,item_id,ce,kind,answer) VALUES(?,?,?,?,?)",("REVIEWREC","rcase","1.a","case",json.dumps("modelo")));db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("REVIEWREC","q1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.execute("INSERT OR REPLACE INTO ai_settings(id,enabled,base_url,api_key,model,rubric,confidence,auto_kinds,updated_at) VALUES(1,1,'x','k','m','r',.75,?,?)",(json.dumps(["case"]),module.now()));db.commit();db.close()
 monkeypatch.setattr(module,"ai_grade",lambda *args,**kwargs:{"score":70.0,"confidence":.4,"verdict":"partial","feedback":"Revisar","criteria":[]});sh={"X-Student-Token":tok};st=client.post("/api/recovery/start",headers=sh,json={"student_id":"review-rec","course_id":"REVIEWREC","kind":"recovery","item_id":"recovery-final","payload":{}});aid=st.json()["id"];r=client.post(f"/api/recovery/{aid}/submit",headers=sh,json={"payload":{"answers":{"rcase":"respuesta"}}});assert r.status_code==200 and r.json()["status"]=="review";db=module.con();rv=db.execute("SELECT id,source_kind FROM ai_reviews WHERE student_id='review-rec' AND course_id='REVIEWREC' ORDER BY id DESC LIMIT 1").fetchone();db.close();assert rv["source_kind"]=="recovery";d=client.put(f"/api/teacher/ai-reviews/{rv['id']}",headers=H,json={"score":85,"feedback":"Correcta tras revisión","status":"accepted"});assert d.status_code==200,d.text;z=d.json();assert z["source_kind"]=="recovery" and z["recovery_result"]["status"]=="passed" and "1.a" in z["recovery_result"]["passed"];assert z["result"]["ce"]["1.a"]["recovered"] is True and z["result"]["recovery"]==[]


def test_public_config_never_exposes_exam_pin_or_student_lists():
 body={**module.DEFAULT,"exam_enabled":True,"exam_pin":"7391","exam_allowed_students":["alice"],"exam_exempt_students":["bob"]};assert client.put("/api/config/PRIVATECFG",headers=H,json=body).status_code==200;pub=client.get("/api/config/PRIVATECFG");assert pub.status_code==200;d=pub.json();assert "exam_pin" not in d and "exam_allowed_students" not in d and "exam_exempt_students" not in d and d["exam_pin_required"] is True;assert client.get("/api/teacher/config/PRIVATECFG").status_code==401;priv=client.get("/api/teacher/config/PRIVATECFG",headers=H);assert priv.status_code==200 and priv.json()["exam_pin"]=="7391" and priv.json()["exam_allowed_students"]==["alice"]


def test_student_security_boundaries_and_secret_redaction():
 client.post("/api/teacher/students/sec-a",headers=H);client.post("/api/teacher/students/sec-b",headers=H);db=module.con();ta=db.execute("SELECT token FROM students WHERE student_id='sec-a'").fetchone()["token"];tb=db.execute("SELECT token FROM students WHERE student_id='sec-b'").fetchone()["token"];db.commit();db.close();ha={"X-Student-Token":ta};assert client.put("/api/state/sec-a",headers=ha,json={"course_id":"SEC","state":{"x":1}}).status_code==200;assert client.get("/api/state/sec-b?course_id=SEC",headers=ha).status_code==403;assert client.put("/api/state/sec-b",headers=ha,json={"course_id":"SEC","state":{"x":9}}).status_code==403;ai=client.get("/api/teacher/ai-settings",headers=H);assert ai.status_code==200 and "api_key" not in ai.json();assert client.get("/api/teacher/ai-settings",headers=ha).status_code==401

def test_public_portfolio_bank_contains_no_answer_keys():
 client.post("/api/teacher/students/pub-bank",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='pub-bank'").fetchone()["token"];db.close();r=client.get("/api/portfolio/GRH0652",headers={"X-Student-Token":tok});assert r.status_code==200;rj=r.json();assert rj["items"] and all("answer" not in q and "correct" not in q and "solution" not in q for q in rj["items"])


def test_teacher_exceptional_reopen_preserves_original_submission_and_is_audited():
 body={**module.DEFAULT,"exam_enabled":True,"exam_minutes":20};assert client.put("/api/config/REOPEN",headers=H,json=body).status_code==200
 db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("REOPEN","rq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close()
 client.post("/api/teacher/students/reopen-student",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='reopen-student'").fetchone()["token"];db.close();sh={"X-Student-Token":tok}
 st=client.post("/api/exam/start",headers=sh,json={"student_id":"reopen-student","course_id":"REOPEN","kind":"exam","item_id":"final","payload":{}});assert st.status_code==200,st.text;old_id=st.json()["attempt_id"];qid=st.json()["questions"][0]["id"]
 sub=client.post(f"/api/exam/{old_id}/submit",headers=sh,json={"payload":{"answers":{qid:0},"integrity":{}}});assert sub.status_code==200,sub.text
 ro=client.post(f"/api/teacher/exam-monitor/{old_id}/reopen",headers=H,json={"minutes":35,"reason":"Incidencia técnica acreditada"});assert ro.status_code==200,ro.text;z=ro.json();assert z["attempt_id"]!=old_id and z["attempt"]==2 and z["restored_answers"]==1
 db=module.con();old=db.execute("SELECT status,payload FROM attempts WHERE id=?",(old_id,)).fetchone();new=db.execute("SELECT status,payload FROM attempts WHERE id=?",(z["attempt_id"],)).fetchone();audit=db.execute("SELECT * FROM exam_reopen_audit WHERE source_attempt_id=?",(old_id,)).fetchone();db.close()
 assert old["status"]=="submitted";assert json.loads(old["payload"])["score"]==100;assert new["status"]=="started";assert json.loads(new["payload"])["draft_answers"][qid]==0;assert audit["new_attempt_id"]==z["attempt_id"] and audit["reason"]=="Incidencia técnica acreditada" and audit["minutes"]==35
 rs=client.post("/api/exam/start",headers=sh,json={"student_id":"reopen-student","course_id":"REOPEN","kind":"exam","item_id":"final","payload":{}});assert rs.status_code==200,rs.text;assert rs.json()["resumed"] is True and rs.json()["attempt_id"]==z["attempt_id"] and rs.json()["saved_answers"][qid]==0


def test_exam_reopen_requires_reason_and_closed_source():
 body={**module.DEFAULT,"exam_enabled":True};assert client.put("/api/config/REOPENRULE",headers=H,json=body).status_code==200
 db=module.con();db.execute("INSERT OR REPLACE INTO exam_banks(course_id,question_id,ce,question,options,answer,type) VALUES(?,?,?,?,?,?,?)",("REOPENRULE","rrq1","1.a","q",json.dumps(["a","b"]),json.dumps(0),"choice"));db.commit();db.close();client.post("/api/teacher/students/reopen-rule",headers=H);db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='reopen-rule'").fetchone()["token"];db.close();sh={"X-Student-Token":tok}
 st=client.post("/api/exam/start",headers=sh,json={"student_id":"reopen-rule","course_id":"REOPENRULE","kind":"exam","item_id":"final","payload":{}});aid=st.json()["attempt_id"]
 assert client.post(f"/api/teacher/exam-monitor/{aid}/reopen",headers=H,json={"minutes":45,"reason":"motivo suficiente"}).status_code==409
 client.post(f"/api/teacher/exam-monitor/{aid}/finish",headers=H)
 assert client.post(f"/api/teacher/exam-monitor/{aid}/reopen",headers=H,json={"minutes":45,"reason":"x"}).status_code==400


def test_readiness_reports_missing_private_banks_before_exam_use():
 course="READYEMPTY";client.post("/api/teacher/students/ready-user",headers=H)
 rd=client.get(f"/api/teacher/readiness/{course}",headers=H);assert rd.status_code==200;z=rd.json();assert z["ready"] is False and z["checks"]["exam_bank"]["ok"] is False
 cfg={**module.DEFAULT,"exam_enabled":True};assert client.put(f"/api/config/{course}",headers=H,json=cfg).status_code==200
 db=module.con();tok=db.execute("SELECT token FROM students WHERE student_id='ready-user'").fetchone()["token"];db.close()
 start=client.post("/api/exam/start",headers={"X-Student-Token":tok},json={"student_id":"ready-user","course_id":course,"kind":"exam","item_id":"final","payload":{}});assert start.status_code==409


def test_readiness_detects_exam_bank_capacity():
 course="READYBANK";bank={"questions":[{"id":"q1","ce":"x","q":"Q1","options":["a","b"],"answer":0,"type":"choice"},{"id":"q2","ce":"x","q":"Q2","options":["a","b"],"answer":0,"type":"choice"}]}
 assert client.put(f"/api/teacher/exam-bank/{course}",headers=H,json=bank).status_code==200
 cfg={**module.DEFAULT,"exam_enabled":True,"exam_questions_per_ce":3};assert client.put(f"/api/config/{course}",headers=H,json=cfg).status_code==200
 rd=client.get(f"/api/teacher/readiness/{course}",headers=H).json();assert rd["checks"]["exam_bank"]["ok"] is False
 cfg["exam_questions_per_ce"]=2;assert client.put(f"/api/config/{course}",headers=H,json=cfg).status_code==200


def test_teacher_backup_is_valid_sqlite_and_requires_auth():
 assert client.get("/api/teacher/backup").status_code==401
 b=client.get("/api/teacher/backup",headers=H);assert b.status_code==200;assert b.content[:16]==b"SQLite format 3\x00";assert len(b.content)>100
 v=client.post("/api/teacher/backup/validate",headers=H,files={"file":("backup.db",b.content,"application/vnd.sqlite3")});assert v.status_code==200,v.text;z=v.json();assert z["ok"] is True and z["integrity"]=="ok" and "students" in z["counts"]


def test_backup_validator_rejects_non_sqlite():
 v=client.post("/api/teacher/backup/validate",headers=H,files={"file":("bad.db",b"not a database","application/octet-stream")});assert v.status_code==400


def test_restore_requires_confirmation_and_restores_valid_snapshot():
 client.post("/api/teacher/students/pre-restore",headers=H)
 b=client.get("/api/teacher/backup",headers=H);assert b.status_code==200
 client.post("/api/teacher/students/post-backup",headers=H)
 no=client.post("/api/teacher/backup/restore",headers=H,files={"file":("backup.db",b.content,"application/vnd.sqlite3")});assert no.status_code==400
 yes=client.post("/api/teacher/backup/restore",headers={**H,"X-Restore-Confirm":"RESTAURAR"},files={"file":("backup.db",b.content,"application/vnd.sqlite3")});assert yes.status_code==200,yes.text;assert yes.json()["integrity"]=="ok"
 db=module.con();assert db.execute("SELECT 1 FROM students WHERE student_id='pre-restore'").fetchone();assert db.execute("SELECT 1 FROM students WHERE student_id='post-backup'").fetchone() is None;db.close()


def test_all_public_portfolio_banks_have_six_items_per_ce_and_unique_ids():
 from collections import Counter
 for u in range(1,5):
  p=module.Path(module.__file__).resolve().parent/"banks"/f"ut{u}_portfolio.json";items=json.loads(p.read_text(encoding="utf-8"))["items"];ids=[x["id"] for x in items];assert len(ids)==len(set(ids))
  counts=Counter(x["ce"] for x in items);assert counts and all(n>=6 for n in counts.values()),(u,counts)
  assert all(x["kind"] in ("choice","tf","multi","free","order","match") for x in items)


def test_private_portfolio_bank_must_match_public_metadata_and_coverage():
 p=module.Path(module.__file__).resolve().parent/"banks"/"ut2_portfolio.json";items=json.loads(p.read_text(encoding="utf-8"))["items"]
 private=[{"id":x["id"],"ce":x["ce"],"kind":x["kind"],"prompt":"Clave privada","options":[],"answer":True if x["kind"]=="tf" else 0} for x in items]
 assert client.put("/api/teacher/portfolio-bank/GRH0652_UT2",headers=H,json={"items":private[:-1]}).status_code==400
 bad=[dict(x) for x in private];bad[0]["ce"]="9.z";assert client.put("/api/teacher/portfolio-bank/GRH0652_UT2",headers=H,json={"items":bad}).status_code==400
 assert client.put("/api/teacher/portfolio-bank/GRH0652_UT2",headers=H,json={"items":private}).status_code==200


def test_all_scorm_units_include_fullscreen_infographic_viewer():
 root=module.Path(module.__file__).resolve().parents[1]/"scorm"
 for u in range(1,5):
  html=(root/f"ut{u}"/"index.html").read_text(encoding="utf-8");css=(root/f"ut{u}"/"assets"/"style.css").read_text(encoding="utf-8")
  assert "Infografía a pantalla completa" in html
  assert "dblclick" in html and "requestFullscreen" in html and "fullscreenchange" in html
  assert ".infographic-viewer" in css and "object-fit:contain" in css


def test_default_document_rubrics_are_seeded_without_overwrite():
 db=module.con()
 rows=[dict(x) for x in db.execute("SELECT course_id,ce,name,criteria FROM ai_rubrics WHERE course_id IN ('GRH0652_UT1','GRH0652_UT4') ORDER BY course_id,ce")]
 db.close()
 found={(x["course_id"],x["ce"]):x for x in rows}
 assert ("GRH0652_UT1","1.g") in found
 assert ("GRH0652_UT4","4.f") in found
 assert ("GRH0652_UT4","4.e") in found
 for x in found.values():
  criteria=json.loads(x["criteria"])
  assert criteria and abs(sum(float(c["weight"]) for c in criteria)-100)<0.01


def test_document_evidence_teacher_review_e2e():
 course="GRH0652_UT1";sid="doc-e2e"
 created=client.post(f"/api/teacher/students/{sid}",headers=H);assert created.status_code==200
 sh={"X-Student-Token":created.json()["token"]}
 payload={"student_id":sid,"course_id":course,"kind":"portfolio","ce":"1.g","item_id":"1.g-contract-c1","attempt":1,"response":{"modalidad":"indefinido","jornada":"completa","convenio":"aplicable"},"payload":{"activity":"contract-document","review_required":True,"fields_total":3,"fields_completed":3}}
 sent=client.post("/api/evidence",headers=sh,json=payload);assert sent.status_code==200,sent.text;assert sent.json()["score"] is None
 reviews=client.get("/api/teacher/ai-reviews",headers=H,params={"course_id":course});assert reviews.status_code==200
 review=next(x for x in reviews.json() if x["student_id"]==sid and x["item_id"]=="1.g-contract-c1");assert review["status"]=="pending"
 decided=client.put(f"/api/teacher/ai-reviews/{review['id']}",headers=H,json={"score":82,"feedback":"Contrato coherente; revisar detalle formal.","status":"accepted"});assert decided.status_code==200,decided.text
 z=decided.json();assert z["score"]==82 and z["evidence_id"] is not None
 db=module.con();ev=db.execute("SELECT score,correct,payload FROM evidence WHERE id=?",(z["evidence_id"],)).fetchone();db.close()
 assert ev["score"]==82 and ev["correct"]==1
 ep=json.loads(ev["payload"]);assert ep["teacher_decision"]=="accepted" and ep["teacher_feedback"]
 assert z["result"]["ce"]["1.g"]["portfolio"]==82


def test_document_portfolio_attempts_are_server_numbered_and_limited():
 course="GRH0652_UT1";sid="doc-attempts";item="1.g-contract-c2"
 created=client.post(f"/api/teacher/students/{sid}",headers=H);assert created.status_code==200
 sh={"X-Student-Token":created.json()["token"]}
 seen=[]
 for expected in (1,2):
  start=client.post("/api/attempts/start",headers=sh,json={"student_id":sid,"course_id":course,"kind":"portfolio","item_id":item,"payload":{"activity":"contract-document"}});assert start.status_code==200,start.text
  z=start.json();assert z["attempt"]==expected and z["resumed"] is False
  ev=client.post("/api/evidence",headers=sh,json={"student_id":sid,"course_id":course,"kind":"portfolio","ce":"1.g","item_id":item,"attempt":z["attempt"],"response":{"modalidad":"indefinido","jornada":"completa"},"payload":{"activity":"contract-document","review_required":True}});assert ev.status_code==200,ev.text
  done=client.post(f"/api/attempts/{z['id']}/submit",headers=sh,json={"payload":{"activity":"contract-document","evidence_saved":True}});assert done.status_code==200,done.text
  seen.append(z["attempt"])
 third=client.post("/api/attempts/start",headers=sh,json={"student_id":sid,"course_id":course,"kind":"portfolio","item_id":item,"payload":{"activity":"contract-document"}})
 assert third.status_code==409
 db=module.con();attempts=[x["attempt"] for x in db.execute("SELECT attempt FROM evidence WHERE student_id=? AND course_id=? AND item_id=? ORDER BY id",(sid,course,item))];db.close()
 assert attempts==seen==[1,2]


def test_payroll_document_teacher_review_updates_ra4_ce():
 course="GRH0652_UT4";sid="payroll-e2e";item="4.e-payroll-complete"
 created=client.post(f"/api/teacher/students/{sid}",headers=H);assert created.status_code==200
 sh={"X-Student-Token":created.json()["token"]}
 start=client.post("/api/attempts/start",headers=sh,json={"student_id":sid,"course_id":course,"kind":"portfolio","item_id":item,"payload":{"activity":"payroll-document"}});assert start.status_code==200,start.text
 attempt=start.json();assert attempt["attempt"]==1
 sent=client.post("/api/evidence",headers=sh,json={"student_id":sid,"course_id":course,"kind":"portfolio","ce":"4.e","item_id":item,"attempt":attempt["attempt"],"response":{"devengado":"1850","bcc":"2100","liquido":"1491.92"},"payload":{"activity":"payroll-document","review_required":True,"fields_total":3,"fields_correct":3}})
 assert sent.status_code==200,sent.text;assert sent.json()["score"] is None
 closed=client.post(f"/api/attempts/{attempt['id']}/submit",headers=sh,json={"payload":{"activity":"payroll-document","evidence_saved":True}});assert closed.status_code==200
 reviews=client.get("/api/teacher/ai-reviews",headers=H,params={"course_id":course});assert reviews.status_code==200
 review=next(x for x in reviews.json() if x["student_id"]==sid and x["item_id"]==item and x["attempt"]==1);assert review["status"]=="pending"
 decided=client.put(f"/api/teacher/ai-reviews/{review['id']}",headers=H,json={"score":91,"feedback":"Nómina correctamente confeccionada y trazable.","status":"accepted"});assert decided.status_code==200,decided.text
 z=decided.json();assert z["score"]==91 and z["result"]["ce"]["4.e"]["portfolio"]==91
 db=module.con();ev=db.execute("SELECT attempt,score,correct,payload FROM evidence WHERE id=?",(z["evidence_id"],)).fetchone();db.close()
 assert ev["attempt"]==1 and ev["score"]==91 and ev["correct"]==1
 ep=json.loads(ev["payload"]);assert ep["teacher_decision"]=="accepted" and ep["teacher_feedback"]


def test_ut4_private_keys_grade_reclassified_4g_4h_without_public_leak():
 import json
 from pathlib import Path
 public=json.loads((Path(module.__file__).resolve().parent/"banks"/"ut4_portfolio.json").read_text(encoding="utf-8"))["items"]
 answers={
  "4.gp1":0,"4.gp2":[0,1,2,3],"4.gp3":False,"4.gp4":1,"4.gp5":0,"4.gp6":0,
  "4.hp1":0,"4.hp2":1,"4.hp3":[0,1,2,3],"4.hp4":1,"4.hp5":1,"4.hp6":[0,1,2,3,4],
 }
 private=[]
 for q in public:
  answer=answers.get(q["id"])
  if answer is None:
   answer=False if q["kind"]=="tf" else ([0] if q["kind"] in ("multi","order") else 0)
  private.append({"id":q["id"],"ce":q["ce"],"kind":q["kind"],"prompt":q.get("prompt",""),"options":q.get("options",[]),"answer":answer})
 loaded=client.put("/api/teacher/portfolio-bank/GRH0652_UT4",headers=H,json={"items":private})
 assert loaded.status_code==200,loaded.text
 created=client.post("/api/teacher/students/ut4-private-e2e",headers=H);assert created.status_code==200
 sh={"X-Student-Token":created.json()["token"]}
 good=client.post("/api/evidence",headers=sh,json={"student_id":"ut4-private-e2e","course_id":"GRH0652_UT4","kind":"portfolio","ce":"4.g","item_id":"4.gp4","attempt":1,"response":1})
 assert good.status_code==200,good.text
 assert good.json()["correct"] is True and good.json()["score"]==100
 bad=client.post("/api/evidence",headers=sh,json={"student_id":"ut4-private-e2e","course_id":"GRH0652_UT4","kind":"portfolio","ce":"4.h","item_id":"4.hp2","attempt":1,"response":0})
 assert bad.status_code==200,bad.text
 assert bad.json()["correct"] is False and bad.json()["score"]==0
 pub=client.get("/api/portfolio/GRH0652",headers=sh);assert pub.status_code==200
 selected=[x for x in pub.json()["items"] if x["id"] in ("4.gp4","4.hp2")]
 assert len(selected)==2 and all("answer" not in x for x in selected)

import os,tempfile,importlib
os.environ["GRH_TEACHER_TOKEN"]="test-token"
fd,path=tempfile.mkstemp(suffix=".db");os.close(fd);os.environ["GRH_DB"]=path
import app as module
from fastapi.testclient import TestClient
client=TestClient(module.app)
H={"X-Teacher-Token":"test-token"}
def start(kind,item="x",student="s1",course="GRH0652_UT1"):
 return client.post("/api/attempts/start",json={"student_id":student,"course_id":course,"kind":kind,"item_id":item,"payload":{}})
def submit(i,payload=None):return client.post(f"/api/attempts/{i}/submit",json={"payload":payload or {}})
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
 a=client.post("/api/exam/start",json=body);assert a.status_code==200
 b=client.post("/api/exam/start",json=body);assert b.status_code==200;assert b.json()["attempt_id"]==a.json()["attempt_id"];assert b.json()["questions"]==a.json()["questions"]
 answers={q["id"]:0 for q in a.json()["questions"]};done=client.post(f"/api/exam/{a.json()['attempt_id']}/submit",json={"payload":{"answers":answers}});assert done.status_code==200
 assert client.post("/api/exam/start",json=body).status_code==409
def test_config_weights_and_version():
 bad={"portfolio_weight":50,"exam_weight":60};assert client.put("/api/config/GRH0652_UT2",headers=H,json=bad).status_code==400
 good={"portfolio_weight":50,"exam_weight":50,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":False,"exam_questions_per_ce":3,"exam_minutes":45,"require_both_instruments":False}
 r=client.put("/api/config/GRH0652_UT2",headers=H,json=good);assert r.status_code==200;assert r.json()["version"]==1
def test_close_generates_only_failed_recovery():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/CLOSE",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"cq1","ce":"3.c","q":"C","options":[],"answer":True,"type":"tf"},{"id":"fq1","ce":"3.f","q":"F","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/CLOSE",headers=H,json=bank).status_code==200
 for student,score in (("fail",0),("pass",100)):
  for ce,item in (("3.c","pc"),("3.f","pf")):
   assert client.post("/api/evidence",json={"student_id":student,"course_id":"CLOSE","kind":"portfolio","ce":ce,"item_id":item,"attempt":1,"response":"x","correct":score==100,"score":score,"payload":{}}).status_code==200
  st=client.post("/api/exam/start",json={"student_id":student,"course_id":"CLOSE","kind":"exam","item_id":"final"});assert st.status_code==200,st.text
  ans={q["id"]:(True if score==100 else False) for q in st.json()["questions"]}
  assert client.post(f"/api/exam/{st.json()['attempt_id']}/submit",json={"payload":{"answers":ans}}).status_code==200
  forged={"student_id":student,"course_id":"CLOSE","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
  assert client.post("/api/result",json=forged).status_code==200
 r=client.post("/api/teacher/close/CLOSE",headers=H);assert r.status_code==200;assert r.json()["recovery_plans"]==1
 p=client.get("/api/recovery/fail/CLOSE").json()["plan"];assert p["criteria"]==["3.c","3.f"]
 assert client.get("/api/recovery/pass/CLOSE").json()["plan"] is None

def test_exam_snapshot_and_deadline_are_persisted():
    cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
    assert client.put("/api/config/GRH0652_UT4",headers=H,json=cfg).status_code==200
    bank={"questions":[{"id":"tq1","ce":"4.a","q":"A","options":["Sí","No"],"answer":0}]}
    assert client.put("/api/teacher/exam-bank/GRH0652_UT4",headers=H,json=bank).status_code==200
    r=client.post("/api/exam/start",json={"student_id":"timed","course_id":"GRH0652_UT4","kind":"exam","item_id":"final"})
    assert r.status_code==200
    data=r.json()
    assert data["version"] and data["deadline_at"]
    assert data["config"]["exam_minutes"]==45
    again=client.post("/api/exam/start",json={"student_id":"timed","course_id":"GRH0652_UT4","kind":"exam","item_id":"final"})
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
 r=client.post("/api/exam/start",json={"student_id":"typed","course_id":"TYPES","kind":"exam","item_id":"final"});assert r.status_code==200
 qs=r.json()["questions"];assert {q["type"] for q in qs}=={"choice","tf","multi"};assert all("answer" not in q for q in qs)

def test_missing_exam_bank_does_not_consume_attempt():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/ATOMIC",headers=H,json=cfg).status_code==200
 body={"student_id":"atomic","course_id":"ATOMIC","kind":"exam","item_id":"final","payload":{}}
 first=client.post("/api/exam/start",json=body);assert first.status_code==409
 bank={"questions":[{"id":"a1","ce":"a","q":"A","options":["Sí","No"],"answer":0,"type":"choice"}]}
 assert client.put("/api/teacher/exam-bank/ATOMIC",headers=H,json=bank).status_code==200
 second=client.post("/api/exam/start",json=body);assert second.status_code==200
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
 s=client.post("/api/recovery/start",json={"student_id":"rec","course_id":"REC","kind":"recovery","item_id":"ignored","payload":{}});assert s.status_code==200
 answers={"r1":0,"r2":True,"r3":[2,0],"r4":" respuesta "}
 done=client.post(f"/api/recovery/{s.json()['id']}/submit",json={"payload":{"answers":answers}});assert done.status_code==200, done.text
 assert done.json()["status"]=="passed"
 assert done.json()["result"]=={"ce_passed":1,"ce_total":1,"ra_passed":False,"recovery":[]}
 c=module.con();rr=c.execute("SELECT ce_passed,ce_total,ra_passed,recovery FROM results WHERE student_id=? AND course_id=?",("rec","REC")).fetchone();rp=c.execute("SELECT criteria,status FROM recovery_plans WHERE student_id=? AND course_id=?",("rec","REC")).fetchone();c.close()
 assert rr["ce_passed"]==1 and rr["ce_total"]==1 and rr["recovery"]=="[]"
 assert rp["criteria"]=="[]" and rp["status"]=="passed"
 assert client.post("/api/recovery/start",json={"student_id":"rec","course_id":"REC","kind":"recovery","item_id":"ignored","payload":{}}).status_code==409

def test_result_ignores_client_claims_and_recomputes_from_server_evidence():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/AUTH",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"q1","ce":"c1","q":"Q1","options":[],"answer":True,"type":"tf"},{"id":"q2","ce":"c2","q":"Q2","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/AUTH",headers=H,json=bank).status_code==200
 for ce,item,score in [("c1","p1",100),("c2","p2",0)]:
  assert client.post("/api/evidence",json={"student_id":"auth","course_id":"AUTH","kind":"portfolio","ce":ce,"item_id":item,"attempt":1,"response":"x","correct":score==100,"score":score,"payload":{}}).status_code==200
 start=client.post("/api/exam/start",json={"student_id":"auth","course_id":"AUTH","kind":"exam","item_id":"final"});assert start.status_code==200,start.text
 qs=start.json()["questions"];answers={}
 for q in qs: answers[q["id"]]=True if q["ce"]=="c1" else False
 assert client.post(f"/api/exam/{start.json()['attempt_id']}/submit",json={"payload":{"answers":answers}}).status_code==200
 forged={"student_id":"auth","course_id":"AUTH","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
 r=client.post("/api/result",json=forged);assert r.status_code==200,r.text
 d=r.json();assert d["final"]==50.0;assert d["ce_passed"]==1;assert d["ra_passed"] is False;assert d["recovery"]==["c2"]

def test_missing_ce_cannot_disappear_from_authoritative_denominator():
 cfg={"portfolio_weight":40,"exam_weight":60,"pass_score":50,"ce_pass_percent":80,"ce_pass_score":50,"exam_enabled":True,"exam_questions_per_ce":1,"exam_minutes":45,"require_both_instruments":False}
 assert client.put("/api/config/UNIVERSE",headers=H,json=cfg).status_code==200
 bank={"questions":[{"id":"u1","ce":"c1","q":"Q1","options":[],"answer":True,"type":"tf"},{"id":"u2","ce":"c2","q":"Q2","options":[],"answer":True,"type":"tf"}]}
 assert client.put("/api/teacher/exam-bank/UNIVERSE",headers=H,json=bank).status_code==200
 assert client.post("/api/evidence",json={"student_id":"u","course_id":"UNIVERSE","kind":"portfolio","ce":"c1","item_id":"p1","attempt":1,"response":"x","correct":True,"score":100,"payload":{}}).status_code==200
 st=client.post("/api/exam/start",json={"student_id":"u","course_id":"UNIVERSE","kind":"exam","item_id":"final"});assert st.status_code==200
 answers={q["id"]:(True if q["ce"]=="c1" else False) for q in st.json()["questions"]}
 assert client.post(f"/api/exam/{st.json()['attempt_id']}/submit",json={"payload":{"answers":answers}}).status_code==200
 forged={"student_id":"u","course_id":"UNIVERSE","portfolio":100,"exam":100,"final":100,"ce_passed":2,"ce_total":2,"ra_passed":True,"recovery":[]}
 r=client.post("/api/result",json=forged);assert r.status_code==200,r.text
 d=r.json();assert d["ce_total"]==2;assert d["ce"]["c2"]["portfolio"]==0;assert d["ce"]["c2"]["passed"] is False;assert "c2" in d["recovery"]

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
 client.post("/api/result",json={"student_id":"fail","course_id":"GRH0652_UT3","portfolio":50,"exam":40,"final":44,"ce_passed":5,"ce_total":8,"ra_passed":False,"recovery":["3.c","3.f"]})
 client.post("/api/result",json={"student_id":"pass","course_id":"GRH0652_UT3","portfolio":80,"exam":80,"final":80,"ce_passed":8,"ce_total":8,"ra_passed":True,"recovery":[]})
 r=client.post("/api/teacher/close/GRH0652_UT3",headers=H);assert r.status_code==200;assert r.json()["recovery_plans"]==1
 p=client.get("/api/recovery/fail/GRH0652_UT3").json()["plan"];assert p["criteria"]==["3.c","3.f"]
 assert client.get("/api/recovery/pass/GRH0652_UT3").json()["plan"] is None

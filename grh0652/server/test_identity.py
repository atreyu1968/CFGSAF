from fastapi.testclient import TestClient
import app as module

client=TestClient(module.app)
TEACHER={"X-Teacher-Token":"test-token"}

def issue(student):
 r=client.post(f"/api/teacher/students/{student}",headers=TEACHER)
 assert r.status_code==200
 return {"X-Student-Token":r.json()["token"]}

def test_student_identity_required_and_spoofing_rejected():
 alice=issue("alice")
 bob=issue("bob")
 body={"student_id":"alice","course_id":"IDENTITY","kind":"practice","item_id":"p1","payload":{}}
 assert client.post("/api/attempts/start",json=body).status_code==401
 assert client.post("/api/attempts/start",headers=bob,json=body).status_code==403
 ok=client.post("/api/attempts/start",headers=alice,json=body)
 assert ok.status_code==200
 attempt=ok.json()["id"]
 assert client.post(f"/api/attempts/{attempt}/answer",headers=bob,json={"response":"x"}).status_code==403
 assert client.post(f"/api/attempts/{attempt}/submit",headers=bob,json={"payload":{}}).status_code==403
 assert client.post(f"/api/attempts/{attempt}/submit",headers=alice,json={"payload":{}}).status_code==200

def test_state_cannot_be_read_or_written_as_another_student():
 alice=issue("state-alice")
 bob=issue("state-bob")
 payload={"course_id":"IDENTITY","state":{"page":3}}
 assert client.put("/api/state/state-alice",headers=alice,json=payload).status_code==200
 assert client.get("/api/state/state-alice?course_id=IDENTITY",headers=bob).status_code==403
 assert client.put("/api/state/state-alice",headers=bob,json=payload).status_code==403
 assert client.get("/api/state/state-alice?course_id=IDENTITY",headers=alice).json()["state"]["page"]==3

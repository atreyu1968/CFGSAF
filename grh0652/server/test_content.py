import re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={"ut1":[f"1.{x}" for x in "abcdefghi"],"ut2":[f"2.{x}" for x in "abcdef"],"ut3":[f"3.{x}" for x in "abcdefgh"],"ut4":[f"4.{x}" for x in "abcdefghij"]}
def json_const(text,name):
 marker="const "+name+"="
 start=text.find(marker);assert start>=0,f"{name} no localizado"
 start+=len(marker)
 while start<len(text) and text[start].isspace(): start+=1
 opener=text[start]; closer={"{":"}","[":"]"}.get(opener);assert closer,f"{name} no comienza con JSON"
 depth=0; quoted=False; esc=False
 for i in range(start,len(text)):
  ch=text[i]
  if quoted:
   if esc: esc=False
   elif ch=="\\": esc=True
   elif ch=='"': quoted=False
   continue
  if ch=='"': quoted=True
  elif ch==opener: depth+=1
  elif ch==closer:
   depth-=1
   if depth==0:return json.loads(text[start:i+1])
 raise AssertionError(f"fin de {name} no localizado")
def block(text,name,next_name):
 return json_const(text,name)
def test_practice_maps_only_to_own_ce_and_has_six_each():
 for unit,ces in EXPECTED.items():
  text=(ROOT/"scorm"/unit/"index.html").read_text(encoding="utf-8");p=block(text,"PRACTICE","EXAM")
  assert set(p)==set(ces)
  for ce in ces:
   assert len(p[ce])>=6
   assert all(x.get("ce",ce)==ce for x in p[ce])
def test_exam_bank_maps_only_to_own_ce_and_has_depth():
 for unit,ces in EXPECTED.items():
  text=(ROOT/"scorm"/unit/"index.html").read_text(encoding="utf-8")
  bank=json_const(text,"EXAM");found={q["ce"] for q in bank}
  assert found<=set(ces),f"{unit} contiene CE ajenos: {found-set(ces)}"
  for ce in ces:assert sum(q["ce"]==ce for q in bank)>=3,f"{unit} {ce} banco insuficiente"
def test_no_ra1_practice_navigation_in_other_units():
 for unit in ("ut2","ut3","ut4"):
  text=(ROOT/"scorm"/unit/"index.html").read_text(encoding="utf-8")
  nav=text[:text.find('<div class="content">')]
  assert 'data-target="pract-1' not in nav

def test_exam_and_self_assessment_are_separate_in_player():
 for unit in EXPECTED:
  js=(ROOT/"scorm"/unit/"assets"/"scorm.js").read_text(encoding="utf-8")
  assert "let examQuestions=[];" in js
  assert "EXAM.splice(0,EXAM.length,...gate.questions)" not in js
  assert "examQuestions=(gate.questions||[])" in js
  assert "const pool=shuffle([...EXAM])" in js
  assert "Entregar examen</button>" in js

def test_exam_uses_server_deadline_and_server_questions():
    for unit in ("ut1","ut2","ut3","ut4"):
        js=(ROOT/"scorm"/unit/"assets"/"scorm.js").read_text(encoding="utf-8")
        assert "examDeadline=gate.deadline_at||null" in js
        assert "startExamTimer()" in js
        assert "setInterval(updateExamCountdown,1000)" in js
        assert "submitExam(true)" in js
        assert "const answers=examQuestions.map(examAnswer)" in js
        assert "examQuestions.forEach((q,i)=>amap[q.id]=answers[i])" in js
        assert "const answers=EXAM.map(examAnswer)" not in js

def test_recovery_ui_supports_all_server_item_types():
 for unit in ("ut1","ut2","ut3","ut4"):
  js=(ROOT/"scorm"/unit/"assets"/"scorm.js").read_text(encoding="utf-8")
  assert "i.kind==='multi'" in js
  assert "type=\"checkbox\"" in js
  assert "i.kind==='tf'" in js
  assert "value=\"true\"" in js and "value=\"false\"" in js
  assert "i.kind==='free'" in js
  assert "<textarea" in js
  assert "Array.from(document.querySelectorAll" in js
  assert "x.value==='true'" in js

def test_authoritative_portfolio_banks_cover_all_units():
 import json
 expected={"ut1":54,"ut2":36,"ut3":48,"ut4":60}
 for unit,n in expected.items():
  data=json.loads((ROOT/"server"/"banks"/f"{unit}_portfolio.json").read_text(encoding="utf-8"))
  assert len(data["items"])==n
  assert len({x["id"] for x in data["items"]})==n
  assert all(x["ce"] and x["kind"] in {"choice","tf","multi","order","match"} for x in data["items"])


def test_all_units_have_strict_exam_guard_and_incident_log():
 for u in ("ut1","ut2","ut3","ut4"):
  s=(ROOT/"scorm"/u/"assets"/"scorm.js").read_text(encoding="utf-8")
  assert "function examGuard(" in s
  assert "fullscreen_exit" in s and "tab_hidden" in s and "window_blur" in s
  assert "incident_log" in s and "examIncidentLog" in s

def test_teacher_has_additio_export():
 s=(ROOT/"teacher.html").read_text(encoding="utf-8")
 assert "exportAdditio" in s and "_Additio.csv" in s and "CE '+x" in s


def test_all_units_have_offline_exam_draft_and_sync_status():
 for ut in ("ut1","ut2","ut3","ut4"):
  js=(ROOT/"scorm"/ut/"assets"/"scorm.js").read_text(encoding="utf-8")
  assert "examDraftKey" in js
  assert "localStorage.setItem(examDraftKey()" in js
  assert "Sin conexión · pendiente" in js
  assert "Reconectando…" in js
  assert "addEventListener('online'" in js
  assert "syncPendingExamDraft" in js


def test_theory_is_not_schematic_in_ra2_ra3_ra4():
 minimum={"ut2":220,"ut3":220,"ut4":200}
 for unit,floor in minimum.items():
  html=(ROOT/"scorm"/unit/"index.html").read_text(encoding="utf-8")
  blocks=re.findall(r'<section class="screen" id="teoria-\d+">(.*?)(?=<section class="screen"|$)',html,re.S)
  assert len(blocks)>=11
  for i,b in enumerate(blocks,1):
   plain=re.sub(r'<[^>]+>',' ',b);words=re.findall(r'\b[\wÁÉÍÓÚÜÑáéíóúüñ]+\b',plain)
   assert len(words)>=floor,f"{unit} teoria-{i} demasiado esquemática: {len(words)} palabras"


def test_portfolio_banks_are_varied_and_orders_are_populated():
 for unit in (2,3,4):
  data=json.loads((ROOT/"server"/"banks"/f"ut{unit}_portfolio.json").read_text(encoding="utf-8"))
  items=data["items"]
  groups={}
  for item in items:
   groups.setdefault(item["ce"],[]).append(item)
  assert all(len(v)>=6 for v in groups.values())
  for ce,group in groups.items():
   prompts=[x["prompt"].strip().lower() for x in group]
   assert len(set(prompts))==len(prompts),f"{unit} {ce}: enunciados duplicados"
   for item in group:
    if item["kind"]=="order":
     assert len(item.get("options",[]))>=4,f"{unit} {ce}: ordenación vacía"
     assert len(set(item["options"]))==len(item["options"])


def test_ut4_embedded_questions_follow_official_ce_boundaries():
 html=(ROOT/"scorm"/"ut4"/"index.html").read_text(encoding="utf-8")
 assert html.count('"ce":"4.h","type":"choice"')>=12
 assert '"id":"4hqx1","ce":"4.h"' in html and "declaración-liquidación" in html
 assert '"id":"4eqx7","ce":"4.e"' in html and "Finiquito:" in html
 assert '"id":"4gqx3","ce":"4.g"' in html and "fecha de presentación" in html
 assert '"id":"4gq7","ce":"4.g"' not in html

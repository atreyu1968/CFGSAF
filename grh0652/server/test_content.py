import re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={"ut1":[f"1.{x}" for x in "abcdefghi"],"ut2":[f"2.{x}" for x in "abcdef"],"ut3":[f"3.{x}" for x in "abcdefgh"],"ut4":[f"4.{x}" for x in "abcdefghij"]}
def block(text,name,next_name):
 m=re.search(r"const "+name+r"=(.*?); const "+next_name+r"=",text,re.S);assert m,f"{name} no localizado";return json.loads(m.group(1))
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
  start=text.find("const EXAM=");assert start>=0,f"EXAM no localizado {unit}"
  raw=text[start+len("const EXAM="):]
  markers=[x for x in (raw.find("; const "),raw.find(";</script>")) if x>=0]
  assert markers,f"fin EXAM no localizado {unit}"
  bank=json.loads(raw[:min(markers)]);found={q["ce"] for q in bank}
  assert found<=set(ces),f"{unit} contiene CE ajenos: {found-set(ces)}"
  for ce in ces:assert sum(q["ce"]==ce for q in bank)>=3,f"{unit} {ce} banco insuficiente"
def test_no_ra1_practice_navigation_in_other_units():
 for unit in ("ut2","ut3","ut4"):
  text=(ROOT/"scorm"/unit/"index.html").read_text(encoding="utf-8")
  nav=text[:text.find('<div class="content">')]
  assert 'data-target="pract-1' not in nav

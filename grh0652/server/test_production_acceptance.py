import csv,io
import pytest
import production_acceptance as p

def ready_payload(course="GRH0652_UT1"):
 ces=["1.a","1.b"]
 return {
  "course_id":course,
  "ready":True,
  "checks":{
   "students":{"ok":True,"count":2},
   "portfolio_keys":{"ok":True,"count":12,"expected_count":12,"missing":[],"extra":[],"stale":[],"metadata_mismatch":[]},
   "exam_bank":{"ok":True,"counts":{ce:3 for ce in ces},"required_per_ce":3,"expected_ce":ces},
   "recovery_bank":{"ok":True,"counts":{ce:2 for ce in ces},"required_per_ce":2,"expected_ce":ces},
   "origins":{"ok":True,"count":1},
  },
 }

def test_production_acceptance_readiness_requires_two_recovery_items_per_ce():
 z=ready_payload()
 assert p.validate_readiness_payload("GRH0652_UT1",z) is True
 z["checks"]["recovery_bank"]["counts"]["1.a"]=1
 z["checks"]["recovery_bank"]["ok"]=False
 z["ready"]=False
 with pytest.raises(p.AcceptanceError,match="recuperación insuficiente"):
  p.validate_readiness_payload("GRH0652_UT1",z)

def test_production_acceptance_rejects_stale_portfolio():
 z=ready_payload();z["checks"]["portfolio_keys"]["ok"]=False;z["checks"]["portfolio_keys"]["stale"]=["x"];z["ready"]=False
 with pytest.raises(p.AcceptanceError,match="Portafolio"):
  p.validate_readiness_payload("GRH0652_UT1",z)

def test_production_acceptance_validates_additio_contract():
 raw='\ufeff"Alumno";"CE 1.a";"Portafolio";"Examen";"RA"\r\n"A01";"100";"100";"80";"88"\r\n'.encode("utf-8")
 out=p.validate_additio_csv(raw)
 assert out=={"rows":1,"columns":5}

def test_production_acceptance_rejects_non_excel_friendly_additio():
 raw=b'Alumno,Portafolio,Examen,RA\nA01,100,80,88\n'
 with pytest.raises(p.AcceptanceError):
  p.validate_additio_csv(raw)

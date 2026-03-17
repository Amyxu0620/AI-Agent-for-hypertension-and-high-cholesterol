from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app import schemas, crud
from app.coordinator import (
    run_caregiver_daily_summary,
    run_family_coordination,
    run_risk_detection,
    run_location_alert,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Caregiver & Family Agent")


@app.get("/")
def root():
    return {"message": "Caregiver & Family Agent API is running"}


@app.post("/patients")
def create_patient(payload: schemas.PatientCreate, db: Session = Depends(get_db)):
    return crud.create_patient(db, payload)


@app.post("/daily-logs")
def create_daily_log(payload: schemas.DailyLogCreate, db: Session = Depends(get_db)):
    return crud.create_daily_log(db, payload)


@app.post("/metrics")
def create_metric(payload: schemas.HealthMetricCreate, db: Session = Depends(get_db)):
    return crud.create_health_metric(db, payload)


@app.post("/visits")
def create_visit(payload: schemas.VisitLogCreate, db: Session = Depends(get_db)):
    return crud.create_visit_log(db, payload)


@app.post("/run/caregiver-summary/{patient_id}")
def api_caregiver_summary(patient_id: int, db: Session = Depends(get_db)):
    result = run_caregiver_daily_summary(db, patient_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/run/family-coordination/{patient_id}")
def api_family_coordination(patient_id: int, db: Session = Depends(get_db)):
    result = run_family_coordination(db, patient_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/run/risk-detection/{patient_id}")
def api_risk_detection(patient_id: int, db: Session = Depends(get_db)):
    result = run_risk_detection(db, patient_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/run/location-alert")
def api_location_alert(payload: schemas.LocationEventCreate, db: Session = Depends(get_db)):
    result = run_location_alert(db, payload.patient_id, payload.geofence_type, payload.event_type)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

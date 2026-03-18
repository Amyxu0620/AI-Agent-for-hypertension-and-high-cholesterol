from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models, schemas
def create_patient(db: Session, payload: schemas.PatientCreate):
    obj = models.Patient(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
def create_daily_log(db: Session, payload: schemas.DailyLogCreate):
    obj = models.DailyLog(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
def create_health_metric(db: Session, payload: schemas.HealthMetricCreate):
    obj = models.HealthMetric(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
def create_visit_log(db: Session, payload: schemas.VisitLogCreate):
    obj = models.VisitLog(**payload.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
def create_alert_log(db: Session, patient_id: int, severity: str, alert_type: str, message: str):
    obj = models.AlertLog(
        patient_id=patient_id,
        severity=severity,
        alert_type=alert_type,
        message=message
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()
def get_latest_daily_log(db: Session, patient_id: int):
    return (
        db.query(models.DailyLog)
        .filter(models.DailyLog.patient_id == patient_id)
        .order_by(models.DailyLog.log_date.desc())
        .first()
    )
def get_daily_logs_last_n_days(db: Session, patient_id: int, days: int = 7):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.DailyLog)
        .filter(
            models.DailyLog.patient_id == patient_id,
            models.DailyLog.log_date >= since
        )
        .order_by(models.DailyLog.log_date.asc())
        .all()
    )
def get_metrics_last_n_days(db: Session, patient_id: int, days: int = 7):
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.HealthMetric)
        .filter(
            models.HealthMetric.patient_id == patient_id,
            models.HealthMetric.recorded_at >= since
        )
        .order_by(models.HealthMetric.recorded_at.asc())
        .all()
    )
def get_last_visit_for_family_member(db: Session, patient_id: int, family_email: str):
    return (
        db.query(models.VisitLog)
        .filter(
            models.VisitLog.patient_id == patient_id,
            models.VisitLog.family_member_email == family_email
        )
        .order_by(models.VisitLog.visited_at.desc())
        .first()
    )

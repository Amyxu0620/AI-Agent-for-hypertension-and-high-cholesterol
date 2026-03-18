
from caregiver_agent.app.db import SessionLocal
from caregiver_agent.app import crud, schemas
from caregiver_agent.app.crud import get_patient

def sync_state_to_caregiver_db(state):
    db = SessionLocal()
    try:
        patient_id = state.get("patient_id", 1)
        patient = get_patient(db, patient_id)

        if not patient:
            payload = schemas.PatientCreate(
                name=state.get("patient") or state.get("name", ""),
                self_dependent=state.get("caregiver_info", {}).get("self_dependent", True),
                caregiver_email=state.get("caregiver_info", {}).get("caregiver_email", ""),
                family_emails=",".join(state.get("caregiver_info", {}).get("family_emails", []))
            )
            crud.create_patient(db, payload)

        daily = state.get("daily_log", {})

        crud.create_daily_log(db, schemas.DailyLogCreate(
            patient_id=patient_id,
            sleep_hours=daily.get("sleep_hours", 0),
            calories_intake=daily.get("calories_intake", 0),
            nutrition_level=daily.get("nutrition_level", ""),
            exercise_intensity=daily.get("exercise_intensity", ""),
            calories_burnt=daily.get("calories_burnt", 0),
            steps=state.get("steps_today", 0),
            emotional_state=daily.get("emotional_state", ""),
            needs_bath=daily.get("needs_bath", False),
            needs_haircut=daily.get("needs_haircut", False),
            other_care_needs=daily.get("other_care_needs", "")
        ))

        for metric in state.get("health_metrics", []):
            metric_type = metric.get("metric_type")
            if metric_type:
                crud.create_health_metric(db, schemas.HealthMetricCreate(
                    patient_id=patient_id,
                    metric_type=metric_type,
                    value=metric.get("value", 0),
                    unit=metric.get("unit", "")
                ))
    finally:
        db.close()

def handle_caregiver():
    state = load_state()
    sync_state_to_caregiver_db(state)

    db = SessionLocal()
    try:
        patient_id = state.get("patient_id", 1)
        summary = run_caregiver_daily_summary(db, patient_id)
        risks = run_risk_detection(db, patient_id)
        family = run_family_coordination(db, patient_id)
        return {
            "summary": summary,
            "risks": risks,
            "family": family
        }
    finally:
        db.close()

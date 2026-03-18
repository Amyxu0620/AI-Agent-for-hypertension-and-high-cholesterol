import json
from copy import deepcopy
from pathlib import Path
from datetime import datetime

# Paths / Shared State

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
JSON_PATH = PROJECT_ROOT / "patient_data.json"

DEFAULT_STATE = {
    "patient_id": 1,
    "patient": "Mr Tan",
    "name": "Mr Tan",
    "age": 68,
    "conditions": [],
    "medications": [],
    "appointments": [],
    "symptoms_today": [],
    "meals_today": [],
    "steps_today": 0,
    "diet_preferences": [],
    "lifestyle_tips": [],
    "alerts": [],
    "caregiver_info": {
        "caregiver_email": "",
        "family_emails": [],
        "self_dependent": True
    },
    "daily_log": {
        "sleep_hours": 0,
        "calories_intake": 0,
        "nutrition_level": "",
        "exercise_intensity": "",
        "calories_burnt": 0,
        "emotional_state": "",
        "needs_bath": False,
        "needs_haircut": False,
        "other_care_needs": ""
    },
    "health_metrics": []
}


def load_state() -> dict:
    if not JSON_PATH.exists():
        save_state(deepcopy(DEFAULT_STATE))
        return deepcopy(DEFAULT_STATE)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = deepcopy(DEFAULT_STATE)
    merged.update(data)

    if isinstance(data.get("caregiver_info"), dict):
        merged["caregiver_info"].update(data["caregiver_info"])

    if isinstance(data.get("daily_log"), dict):
        merged["daily_log"].update(data["daily_log"])

    return merged


def save_state(state: dict) -> None:
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def append_alert(
    state: dict,
    alert_type: str,
    message: str,
    severity: str = "info",
    source: str = "orchestrator"
) -> None:
    state.setdefault("alerts", [])
    state["alerts"].append({
        "type": alert_type,
        "message": message,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "source": source
    })

# Agent Imports

# Symptoms agent
from symptoms_agent import handle_symptom_message

# Diet & lifestyle agent
from diet&lifestyle_agent import handle_user_query as handle_diet_query

# Appointment agent
from appointment_agent import run_previsit, run_clinician_summary

# Medication agent
from medication_agent import (
    get_reminders,
    check_missed_doses,
    get_schedule,
    mark_taken,
    add_medication,
    remove_medication,
)

# Caregiver agent (DB-based)
from database.db import SessionLocal
from caregiver_agent.app import crud, schemas
from caregiver_agent.app.crud import get_patient
from caregiver_agent.app.coordinator import (
    run_caregiver_daily_summary,
    run_family_coordination,
    run_risk_detection,
    run_location_alert,
)


# Sync Shared JSON -> Caregiver DB

def sync_state_to_caregiver_db(state: dict) -> None:
    db = SessionLocal()
    try:
        patient_id = state.get("patient_id", 1)
        patient_name = state.get("patient") or state.get("name", "Unknown Patient")
        caregiver_info = state.get("caregiver_info", {})
        family_emails = caregiver_info.get("family_emails", [])

        patient = get_patient(db, patient_id)

        if not patient:
            payload = schemas.PatientCreate(
                name=patient_name,
                self_dependent=caregiver_info.get("self_dependent", True),
                caregiver_email=caregiver_info.get("caregiver_email", ""),
                family_emails=",".join(family_emails)
            )
            crud.create_patient(db, payload)

        daily = state.get("daily_log", {})

        crud.create_daily_log(
            db,
            schemas.DailyLogCreate(
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
            )
        )

        for metric in state.get("health_metrics", []):
            metric_type = metric.get("metric_type", "")
            if not metric_type:
                continue

            crud.create_health_metric(
                db,
                schemas.HealthMetricCreate(
                    patient_id=patient_id,
                    metric_type=metric_type,
                    value=metric.get("value", 0),
                    unit=metric.get("unit", "")
                )
            )

    finally:
        db.close()

# Orchestrator Handlers

def handle_symptom(query: str) -> dict:
    state = load_state()
    reply = handle_symptom_message(state, query)
    save_state(state)

    return {
        "agent": "symptoms",
        "reply": reply,
        "state": state
    }


def handle_diet(query: str) -> dict:
    state = load_state()
    reply = handle_diet_query(state, query)
    save_state(state)

    return {
        "agent": "diet_lifestyle",
        "reply": reply,
        "state": state
    }


def handle_medication_overview() -> dict:
    state = load_state()

    reminders = get_reminders(state)
    missed = check_missed_doses(state)
    schedule = get_schedule(state)

    for med_name in missed:
        append_alert(
            state,
            alert_type="MISSED_MEDICATION",
            message=f"Possible missed dose: {med_name}",
            severity="caution",
            source="medication_agent"
        )

    save_state(state)

    return {
        "agent": "medication",
        "reminders": reminders,
        "missed": missed,
        "schedule": schedule,
        "state": state
    }


def handle_mark_medication_taken(med_name: str) -> dict:
    state = load_state()
    mark_taken(state, med_name)
    save_state(state)

    return {
        "agent": "medication",
        "message": f"Marked '{med_name}' as taken.",
        "state": state
    }


def handle_add_medication(
    med: str,
    time: str,
    condition: str,
    frequency: str,
    reminder: bool = True
) -> dict:
    state = load_state()
    add_medication(state, med, time, condition, frequency, reminder)
    save_state(state)

    return {
        "agent": "medication",
        "message": f"Added medication '{med}'.",
        "state": state
    }


def handle_remove_medication(med_name: str) -> dict:
    state = load_state()
    remove_medication(state, med_name)
    save_state(state)

    return {
        "agent": "medication",
        "message": f"Removed medication '{med_name}'.",
        "state": state
    }


def handle_previsit() -> dict:
    state = load_state()
    previsit_text = run_previsit(state)
    save_state(state)

    return {
        "agent": "appointment_previsit",
        "previsit": previsit_text,
        "state": state
    }


def handle_clinician_summary() -> dict:
    state = load_state()
    summary_text, pdf_path = run_clinician_summary(state)
    save_state(state)

    return {
        "agent": "appointment_summary",
        "summary": summary_text,
        "pdf_path": pdf_path,
        "state": state
    }


def handle_caregiver() -> dict:
    state = load_state()
    sync_state_to_caregiver_db(state)

    db = SessionLocal()
    try:
        patient_id = state.get("patient_id", 1)

        daily_summary_result = run_caregiver_daily_summary(db, patient_id)
        risk_result = run_risk_detection(db, patient_id)
        family_result = run_family_coordination(db, patient_id)

        return {
            "agent": "caregiver",
            "daily_summary": daily_summary_result,
            "risk_detection": risk_result,
            "family_coordination": family_result
        }
    finally:
        db.close()


def handle_location_alert(geofence_type: str, event_type: str) -> dict:
    state = load_state()
    sync_state_to_caregiver_db(state)

    db = SessionLocal()
    try:
        patient_id = state.get("patient_id", 1)
        result = run_location_alert(db, patient_id, geofence_type, event_type)
        return {
            "agent": "caregiver_location",
            "result": result
        }
    finally:
        db.close()

# Master Router

def orchestrate_user_request(agent: str, query: str = "", **kwargs) -> dict:
    """
    Main entry point for the orchestrator.

    Supported agent values:
    - "symptoms"
    - "diet"
    - "medication"
    - "medication_mark_taken"
    - "medication_add"
    - "medication_remove"
    - "appointment_previsit"
    - "appointment_summary"
    - "caregiver"
    - "location_alert"
    """

    if agent == "symptoms":
        return handle_symptom(query)

    if agent == "diet":
        return handle_diet(query)

    if agent == "medication":
        return handle_medication_overview()

    if agent == "medication_mark_taken":
        med_name = kwargs.get("med_name", "")
        if not med_name:
            return {"error": "Missing med_name"}
        return handle_mark_medication_taken(med_name)

    if agent == "medication_add":
        med = kwargs.get("med", "")
        time = kwargs.get("time", "")
        condition = kwargs.get("condition", "")
        frequency = kwargs.get("frequency", "")
        reminder = kwargs.get("reminder", True)

        if not med or not time or not condition or not frequency:
            return {"error": "Missing one of: med, time, condition, frequency"}

        return handle_add_medication(med, time, condition, frequency, reminder)

    if agent == "medication_remove":
        med_name = kwargs.get("med_name", "")
        if not med_name:
            return {"error": "Missing med_name"}
        return handle_remove_medication(med_name)

    if agent == "appointment_previsit":
        return handle_previsit()

    if agent == "appointment_summary":
        return handle_clinician_summary()

    if agent == "caregiver":
        return handle_caregiver()

    if agent == "location_alert":
        geofence_type = kwargs.get("geofence_type", "")
        event_type = kwargs.get("event_type", "")
        if not geofence_type or not event_type:
            return {"error": "Missing geofence_type or event_type"}
        return handle_location_alert(geofence_type, event_type)

    return {"error": f"Unknown agent: {agent}"}

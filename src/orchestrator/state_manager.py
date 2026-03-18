import json
from pathlib import Path
from copy import deepcopy

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_PATH = BASE_DIR / "patient_data.json"

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

def load_state():
    if not JSON_PATH.exists():
        save_state(deepcopy(DEFAULT_STATE))
        return deepcopy(DEFAULT_STATE)

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = deepcopy(DEFAULT_STATE)
    merged.update(data)

    if "caregiver_info" in data:
        merged["caregiver_info"].update(data["caregiver_info"])
    if "daily_log" in data:
        merged["daily_log"].update(data["daily_log"])

    return merged

def save_state(state):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

def append_alert(state, alert_type, message, severity="info", source="orchestrator"):
    state["alerts"].append({
        "type": alert_type,
        "message": message,
        "severity": severity,
        "source": source
    })

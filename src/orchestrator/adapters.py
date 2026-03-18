from datetime import datetime

def to_appointment_format(state: dict) -> dict:
    return state

def to_symptom_format(state: dict) -> dict:
    return state

def to_medication_format(state: dict) -> dict:
    return state

def to_caregiver_payload(state: dict) -> dict:
    daily = state.get("daily_log", {})
    return {
        "patient_name": state.get("patient") or state.get("name", ""),
        "self_dependent": state.get("caregiver_info", {}).get("self_dependent", True),
        "sleep_hours": daily.get("sleep_hours", 0),
        "food": {
            "calories_intake": daily.get("calories_intake", 0),
            "nutrition_level": daily.get("nutrition_level", "")
        },
        "exercise": {
            "intensity": daily.get("exercise_intensity", ""),
            "calories_burnt": daily.get("calories_burnt", 0),
            "steps": state.get("steps_today", 0)
        },
        "emotional_state": daily.get("emotional_state", ""),
        "care_needs": {
            "bath": daily.get("needs_bath", False),
            "haircut": daily.get("needs_haircut", False),
            "other": daily.get("other_care_needs", "")
        }
    }

def latest_metric_map(state: dict) -> dict:
    result = {}
    for item in state.get("health_metrics", []):
        key = item.get("metric_type")
        if key:
            result[key] = item
    return result

def now_iso():
    return datetime.now().isoformat()

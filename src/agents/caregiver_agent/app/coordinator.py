from app.crud import (
    get_patient,
    get_latest_daily_log,
    get_daily_logs_last_n_days,
    get_metrics_last_n_days,
    get_last_visit_for_family_member,
    create_alert_log,
)
from app.bedrock_client import generate_caregiver_summary
from app.email_service import send_email
from app.chart_service import generate_weekly_charts
from app.risk_service import detect_risks
from app.family_service import send_family_weekly_update, send_family_visit_reminders
from app.location_service import handle_location_event


def run_caregiver_daily_summary(db, patient_id: int):
    patient = get_patient(db, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    latest_log = get_latest_daily_log(db, patient_id)
    if not latest_log:
        return {"error": "No daily log found"}

    payload = {
        "patient_name": patient.name,
        "self_dependent": patient.self_dependent,
        "sleep_hours": latest_log.sleep_hours,
        "food": {
            "calories_intake": latest_log.calories_intake,
            "nutrition_level": latest_log.nutrition_level,
        },
        "exercise": {
            "intensity": latest_log.exercise_intensity,
            "calories_burnt": latest_log.calories_burnt,
            "steps": latest_log.steps,
        },
        "emotional_state": latest_log.emotional_state,
        "care_needs": {
            "bath": latest_log.needs_bath,
            "haircut": latest_log.needs_haircut,
            "other": latest_log.other_care_needs,
        }
    }

    summary = generate_caregiver_summary(payload)

    send_email(
        to_addresses=[patient.caregiver_email],
        subject=f"Daily Caregiver Summary - {patient.name}",
        html_body=f"<h2>Daily Caregiver Summary</h2><p>{summary.replace(chr(10), '<br>')}</p>",
        text_body=summary
    )

    create_alert_log(db, patient_id, "info", "summary", "Daily caregiver summary sent.")
    return {"message": "Daily caregiver summary sent", "summary": summary}


def run_family_coordination(db, patient_id: int):
    patient = get_patient(db, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    metrics = get_metrics_last_n_days(db, patient_id, days=7)
    chart_paths = generate_weekly_charts(metrics, patient_id) if metrics else []

    weekly_result = send_family_weekly_update(patient, chart_paths)

    reminder_result = send_family_visit_reminders(
        patient,
        lambda email: get_last_visit_for_family_member(db, patient_id, email)
    )

    return {
        "message": "Family coordination completed",
        "weekly_update": weekly_result,
        "visit_reminders": reminder_result
    }


def run_risk_detection(db, patient_id: int):
    patient = get_patient(db, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    daily_logs = get_daily_logs_last_n_days(db, patient_id, days=7)
    metrics = get_metrics_last_n_days(db, patient_id, days=7)

    alerts = detect_risks(daily_logs, metrics)

    for alert in alerts:
        create_alert_log(
            db,
            patient_id,
            alert["severity"],
            alert["alert_type"],
            alert["message"]
        )

        if alert["severity"] in {"caution", "urgent"}:
            send_email(
                to_addresses=[patient.caregiver_email],
                subject=f"Risk Alert - {patient.name}",
                html_body=f"<p>{alert['message']}</p>",
                text_body=alert["message"]
            )

    return {"message": "Risk detection completed", "alerts": alerts}


def run_location_alert(db, patient_id: int, geofence_type: str, event_type: str):
    patient = get_patient(db, patient_id)
    if not patient:
        return {"error": "Patient not found"}

    result = handle_location_event(patient, geofence_type, event_type)

    if result["handled"]:
        create_alert_log(
            db,
            patient_id,
            result["severity"],
            "location",
            result["message"]
        )

    return result

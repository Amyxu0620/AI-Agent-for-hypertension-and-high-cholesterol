from app.email_service import send_email
from app.utils import split_emails


def handle_location_event(patient, geofence_type: str, event_type: str):
    recipients = [patient.caregiver_email] + split_emails(patient.family_emails)

    geofence_type = geofence_type.lower()
    event_type = event_type.upper()

    if geofence_type in {"hospital", "clinic"} and event_type == "ENTER":
        subject = f"{patient.name} has arrived at a medical facility"
        text = f"{patient.name} has arrived at a hospital or clinic."
        severity = "info"

    elif geofence_type == "danger_zone" and event_type == "ENTER":
        subject = f"Urgent alert for {patient.name}"
        text = f"{patient.name} may be in a potentially unsafe situation. Please check immediately."
        severity = "urgent"

    else:
        return {
            "handled": False,
            "severity": None,
            "message": "No notification required for this location event."
        }

    send_email(
        to_addresses=recipients,
        subject=subject,
        html_body=f"<p>{text}</p>",
        text_body=text
    )

    return {
        "handled": True,
        "severity": severity,
        "message": text
    }

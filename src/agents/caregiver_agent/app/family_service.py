from datetime import datetime, timedelta
from app.utils import split_emails
from app.email_service import send_email
from app.config import ALERT_FAMILY_AFTER_DAYS


def send_family_weekly_update(patient, chart_paths):
    recipients = split_emails(patient.family_emails)
    if not recipients:
        return {"message": "No family emails configured", "recipients": []}

    html_body = f"""
    <h2>Weekly Family Update for {patient.name}</h2>
    <p>This weekly update summarizes the patient’s recent trends and engagement.</p>
    <p>Generated chart files:</p>
    <ul>
        {''.join(f'<li>{path}</li>' for path in chart_paths)}
    </ul>
    <p>Please check in regularly and contact the caregiver if any concerns arise.</p>
    """

    send_email(
        to_addresses=recipients,
        subject=f"Weekly Family Update - {patient.name}",
        html_body=html_body,
        text_body=f"Weekly update for {patient.name}. Generated charts: {', '.join(chart_paths)}"
    )

    return {"message": "Family weekly update sent", "recipients": recipients}


def send_family_visit_reminders(patient, get_last_visit_callback):
    recipients = split_emails(patient.family_emails)
    reminded = []
    threshold = datetime.utcnow() - timedelta(days=ALERT_FAMILY_AFTER_DAYS)

    for email in recipients:
        last_visit = get_last_visit_callback(email)
        if last_visit is None or last_visit.visited_at < threshold:
            subject = f"Check-in Reminder for {patient.name}"
            text = f"You have not visited or checked in on {patient.name} in over {ALERT_FAMILY_AFTER_DAYS} days."
            html = f"<p>{text}</p>"

            send_email([email], subject, html, text)
            reminded.append(email)

    return {"message": "Visit reminders processed", "reminded": reminded}

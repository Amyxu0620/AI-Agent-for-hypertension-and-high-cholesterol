from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
import boto3
import json
from botocore.exceptions import ClientError
import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

region = os.getenv("AWS_REGION")
model_id = os.getenv("BEDROCK_MODEL_ID_INFERENCE") or os.getenv("BEDROCK_MODEL_ID")
if not region or not model_id:
    raise ValueError("Missing required env vars: AWS_REGION and BEDROCK_MODEL_ID must be set.")
bedrock = boto3.client("bedrock-runtime", region_name=region)

# ── Schedule functions ─────────────────────────────────────────────────────────

def get_med_schedule(patient):
    return patient.setdefault("medications", [])

def get_taken_log(patient):
    return [m["name"] for m in patient.get("medications", []) if m.get("taken")]

def add_medication(patient, med, time, condition, frequency, reminder=True):
    patient.setdefault("medications", [])
    patient["medications"].append({
        "name": med,
        "dose": "",
        "time": time,
        "taken": False,
        "condition": condition,
        "frequency": frequency,
        "reminder": reminder
    })

def mark_taken(patient, med_name):
    patient.setdefault("medications", [])
    for item in patient["medications"]:
        if item["name"] == med_name:
            item["taken"] = True
            break

def is_due_today(item):
    today = datetime.now().weekday()
    if item["frequency"] == "daily":
        return True
    if item["frequency"] == "weekly":
        return today == 0
    if item["frequency"] == "every 2 weeks":
        return today == 0
    return True

def check_missed_doses(patient):
    now = datetime.now().strftime("%H:%M")
    missed = []
    patient.setdefault("medications", [])
    for item in patient["medications"]:
        if is_due_today(item) and item["time"] < now and item.get("taken", False):
            missed.append(item["name"])
    return missed

def get_reminders(patient):
    now = datetime.now().strftime("%H:%M")
    upcoming = []
    patient.setdefault("medications", [])
    for item in patient["medications"]:
        if item.get("reminder", True) and is_due_today(item) and item["time"] >= now:
            upcoming.append(f"{item['name']} at {item['time']}")
    return upcoming

def get_schedule(patient):
    patient.setdefault("medications", [])
    return patient["medications"]

def remove_medication(patient, med_name):
    patient.setdefault("medications", [])
    patient["medications"] = [
        m for m in patient["medications"] if m["name"] != med_name
    ]

# ── AI Explainer ───────────────────────────────────────────────────────────────

def explain_medication(medication: str, condition: str) -> str:
    if not medication or not condition:
        raise ValueError("Both medication and condition must be non-empty strings.")

    prompt = f"Explain what {medication} does for a patient with {condition}. Use simple, warm, and reassuring words that an elderly person would easily understand."

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 512,
        "system": "You explain medications in simple, friendly language for elderly patients. Avoid medical jargon. Be warm, clear, and reassuring.",
        "messages": [{"role": "user", "content": prompt}]
    })

    try:
        response = bedrock.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body
        )
        result = json.loads(response["body"].read())
        if not result.get("content") or not result["content"][0].get("text"):
            raise ValueError("Unexpected response structure from Bedrock.")
        return result["content"][0]["text"]

    except ClientError as e:
        raise RuntimeError(f"Bedrock API error: {e.response['Error']['Message']}") from e
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected response structure: {e}") from e

# ── Calendar integration ───────────────────────────────────────────────────────

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_recurrence(freq):
    if freq == "daily":
        return ['RRULE:FREQ=DAILY']
    if freq == "weekly":
        return ['RRULE:FREQ=WEEKLY']
    if freq == "biweekly":
        return ['RRULE:FREQ=WEEKLY;INTERVAL=2']
    return []

def create_event(summary, time_str, calendar_id, frequency):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)

    now = datetime.now()
    hour, minute = map(int, time_str.split(":"))
    event_time = now.replace(hour=hour, minute=minute, second=0)

    event = {
        'summary': summary,
        'start': {
            'dateTime': event_time.isoformat(),
            'timeZone': 'Asia/Singapore',
        },
        'end': {
            'dateTime': (event_time + timedelta(minutes=30)).isoformat(),
            'timeZone': 'Asia/Singapore',
        },
        'recurrence': get_recurrence(frequency),
    }

    event = service.events().insert(
        calendarId=calendar_id,
        body=event
    ).execute()

    return event.get('htmlLink')

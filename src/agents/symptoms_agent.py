"""
symptom_agent.py — Person 4
━━━━━━━━━━━━━━━━━━━━━━━━━━
Owned by  : Person 4
Called by  : Person 5 (Orchestrator) via handle_symptom_message(patient, query)
Writes to  : shared patient_data.json  →  symptoms_today, alerts
Read by    : Person 2 (Clinician Summary) reads symptoms_today + alerts

Matches patterns from diet_lifestyle_agent.py:
  - invoke_model() Bedrock call (not converse)
  - load_patient() with fallback default
  - handle_symptom_message(patient, query) signature
"""

import json
import re
import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────────────────

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "..", "patient_data.json")

# ─── JSON Helpers ─────────────────────────────────────────────────────────────

def load_patient():
    if not os.path.exists(JSON_PATH):
        return {
            "patient": "Mr Tan",
            "conditions": ["hypertension", "hyperlipidaemia"],
            "medications": [
                {"name": "Amlodipine", "dose": "5mg", "time": "08:00", "taken": False},
                {"name": "Simvastatin", "dose": "20mg", "time": "21:00", "taken": True}
            ],
            "appointments": [],
            "symptoms_today": [],
            "meals_today": [],
            "steps_today": 0,
            "alerts": []
        }
    with open(JSON_PATH, "r") as f:
        return json.load(f)

def save_patient(patient):
    with open(JSON_PATH, "w") as f:
        json.dump(patient, f, indent=2)

def update_patient_json(patient: dict, symptom: str, risk: str):
    """
    Writes symptom into symptoms_today.
    MEDIUM/HIGH also appends a structured alert for Person 2's clinician summary.
    """
    if symptom not in patient["symptoms_today"]:
        patient["symptoms_today"].append(symptom)

    if risk in ("MEDIUM", "HIGH"):
        alert = {
            "type": f"{risk}_SYMPTOM",
            "symptom": symptom,
            "timestamp": datetime.now().isoformat(),
            "source": "symptom_agent"
        }
        patient["alerts"].append(alert)

    save_patient(patient)

# ─── Bedrock Helper (matches diet_lifestyle_agent.py pattern) ─────────────────

def ask_claude(system_prompt: str, user_message: str) -> str:
    region   = os.getenv("AWS_REGION")
    model_id = os.getenv("BEDROCK_MODEL_ID")
    if model_id and not model_id.startswith("us."):
        model_id = "us." + model_id  

    if not region:
        return "Error: AWS_REGION not found in .env"
    if not model_id:
        return "Error: BEDROCK_MODEL_ID not found in .env"

    try:
        client = boto3.client("bedrock-runtime", region_name=region)

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }

        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )

        result = json.loads(response["body"].read())

        if "content" in result and len(result["content"]) > 0:
            return result["content"][0]["text"]

        return f"Error: Unexpected Bedrock response format: {result}"

    except Exception as e:
        return f"Error calling Bedrock: {str(e)}"

# ─── System Prompt ────────────────────────────────────────────────────────────

def build_system_prompt(patient: dict) -> str:
    med_lines = []
    for m in patient["medications"]:
        status = "✓ taken" if m["taken"] else "✗ NOT taken yet"
        med_lines.append(f"  - {m['name']} {m['dose']} at {m['time']} ({status})")
    meds = "\n".join(med_lines)

    appts = ", ".join(f"{a['type']} on {a['date']}" for a in patient["appointments"]) or "none"
    existing_symptoms = ", ".join(patient["symptoms_today"]) if patient["symptoms_today"] else "none"
    meals = ", ".join(patient["meals_today"]) if patient["meals_today"] else "none"

    return f"""You are a warm, empathetic AI health companion helping {patient['patient']},
an elderly Singaporean patient with {", ".join(patient["conditions"])}.

━━ PATIENT CONTEXT ━━
Conditions  : {", ".join(patient["conditions"])}
Medications :
{meds}
Appointments: {appts}
Meals today : {meals}
Steps today : {patient["steps_today"]}
Symptoms already reported today: {existing_symptoms}

━━ YOUR ROLE ━━
You are NOT a doctor. You must NEVER diagnose. Always recommend professional consultation.

When the patient reports a symptom, you must:

1. CLASSIFY risk as exactly one of: LOW | MEDIUM | HIGH
   Rules:
   - HIGH   → chest pain, breathlessness, severe dizziness, sudden numbness,
               confusion, vision changes, or any symptom alarming given hypertension.
               Tell them to call 995 or go to A&E immediately.
   - MEDIUM → symptom may relate to a medication not yet taken, or something
               worth monitoring. Tell them to check their medication and rest.
               Contact doctor if it persists.
   - LOW    → mild and common. Offer gentle lifestyle advice relevant to their
               meals or activity level today.

2. Respond empathetically in plain, simple English. No medical jargon.
   Mr Tan is in his 60s — keep it warm, like a concerned family member
   who happens to know about health.

3. Always end your conversational reply with:
   "Remember, I am not a doctor. Please consult a healthcare professional
   if you are worried or if your symptoms do not improve."

4. On the very last line, output ONLY this JSON and nothing else after it:
   {{"symptom": "<symptom in 2-4 words>", "risk": "<LOW|MEDIUM|HIGH>", "timestamp": "<ISO 8601>"}}"""

# ─── Core Logic ───────────────────────────────────────────────────────────────

def run_symptom_check(patient: dict, query: str) -> dict:
    full_text = ask_claude(build_system_prompt(patient), query)

    symptom, risk = "unknown symptom", "LOW"
    try:
        matches = re.findall(r'\{[^{}]+\}', full_text)
        if matches:
            log = json.loads(matches[-1])
            symptom = log.get("symptom", symptom)
            risk = log.get("risk", risk).upper()
            # Strip the JSON block from the user-facing reply
            full_text = full_text[:full_text.rfind(matches[-1])].strip()
    except Exception:
        pass  # never crash — always return a reply

    return {
        "reply": full_text,
        "symptom": symptom,
        "risk": risk
    }

# ─── Entry Point for Person 5 ─────────────────────────────────────────────────

def handle_symptom_message(patient: dict, query: str) -> str:
    """
    THIS IS THE ONLY FUNCTION PERSON 5 NEEDS TO CALL.
    Signature matches handle_user_query() in diet_lifestyle_agent.py.

    Person 5 usage:
        from symptom_agent import handle_symptom_message
        reply = handle_symptom_message(patient, "I feel dizzy and a bit breathless")
        send_to_chat(reply)
    """
    result = run_symptom_check(patient, query)
    update_patient_json(patient, result["symptom"], result["risk"])

    print(f"[SYMPTOM AGENT] symptom='{result['symptom']}' risk={result['risk']}")

    return result["reply"]

# ─── Standalone test (Person 4 only) ─────────────────────────────────────────

if __name__ == "__main__":
    patient = load_patient()

    test_cases = [
        "I feel a bit tired today",                        # expect LOW
        "I feel dizzy, maybe I forgot my morning pill",    # expect MEDIUM
        "I have chest pain and I can't breathe properly",  # expect HIGH
    ]

    for msg in test_cases:
        print(f"\n{'━'*50}")
        print(f"Input : {msg}")
        print(f"Reply :\n{handle_symptom_message(patient, msg)}")

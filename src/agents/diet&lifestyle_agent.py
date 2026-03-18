import json
import os
from pathlib import Path
from dotenv import load_dotenv

current = Path(__file__).resolve()
for parent in [current.parent, *current.parents]:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print("Loaded .env from:", env_file)
        break
else:
    print("No .env file found")
print("AWS_REGION =", os.getenv("AWS_REGION"))
print("AWS_ACCESS_KEY_ID =", os.getenv("AWS_ACCESS_KEY_ID"))
print("HAS_SECRET =", bool(os.getenv("AWS_SECRET_ACCESS_KEY")))
print("HAS_SESSION_TOKEN =", bool(os.getenv("AWS_SESSION_TOKEN")))
print("BEDROCK_MODEL_ID_INFERENCE", os.getenv("BEDROCK_MODEL_ID_INFERENCE"))
import boto3


load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Prefer inference profile for this file only.
# Falls back to BEDROCK_MODEL_ID so the rest of the project stays unchanged.
BEDROCK_MODEL_ID = (
    os.getenv("BEDROCK_MODEL_ID_INFERENCE")
    or os.getenv("BEDROCK_MODEL_ID")
)

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=AWS_REGION
)


def chat_with_bedrock(user_message: str) -> str:
    if not BEDROCK_MODEL_ID:
        return "Error: Missing BEDROCK_MODEL_ID_INFERENCE or BEDROCK_MODEL_ID in .env"

    system_prompt = (
        "You are a helpful health and lifestyle assistant. "
        "Give safe, general wellness guidance based on the user's context. "
        "Do not claim to be a doctor. "
        "For emergencies or severe symptoms, advise seeking medical help."
    )

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "temperature": 0.3,
        "system": system_prompt,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_message
                    }
                ]
            }
        ]
    }

    def handle_user_query(patient: dict, query: str) -> str:
    patient_name = patient.get("patient") or patient.get("name", "Patient")
    conditions = ", ".join(patient.get("conditions", [])) or "None"
    symptoms = ", ".join(patient.get("symptoms_today", [])) or "None"
    meals = ", ".join(patient.get("meals_today", [])) or "None"
    steps = patient.get("steps_today", 0)

    daily_log = patient.get("daily_log", {})
    sleep_hours = daily_log.get("sleep_hours", 0)
    emotional_state = daily_log.get("emotional_state", "unknown")
    nutrition_level = daily_log.get("nutrition_level", "unknown")

    full_message = f"""
    Patient context:
    - Name: {patient_name}
    - Conditions: {conditions}
    - Symptoms today: {symptoms}
    - Meals today: {meals}
    - Steps today: {steps}
    - Sleep hours: {sleep_hours}
    - Emotional state: {emotional_state}
    - Nutrition level: {nutrition_level}
    
    User question:
    {query}
    """.strip()

    return chat_with_bedrock(full_message)

    try:
       
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )

        response_body = json.loads(response["body"].read())

        # Claude response format
        if "content" in response_body and len(response_body["content"]) > 0:
            return response_body["content"][0]["text"]

        return f"Unexpected Bedrock response: {response_body}"

    except Exception as e:
        return f"Error calling Bedrock: {str(e)}"


if __name__ == "__main__":
    while True:
        user_input = input("USER: ").strip()
        if user_input.lower() in {"exit", "quit"}:
            break
        reply = chat_with_bedrock(user_input)
        print(f"AGENT: {reply}")

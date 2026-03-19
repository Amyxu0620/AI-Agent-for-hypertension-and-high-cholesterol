import json
import boto3
from app.config import AWS_REGION, BEDROCK_MODEL_ID

bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)

def generate_caregiver_summary(payload: dict) -> str:
    prompt = f"""
You are a caregiver support assistant.
Write a clear, professional caregiver daily summary.
Rules:
- Mention sleep, food, exercise, emotional state.
- Be specific but concise.
- If the patient is not self-dependent and any care needs exist, mention them.
- If no bath/haircut/other care needs exist, omit that section entirely.
- Do not include recommendations unless there is a clear risk.
- If there is a possible concern, begin the relevant sentence with 'Attention needed:'.
Patient data:
{json.dumps(payload, indent=2)}
"""
    response = bedrock.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}]
            }
        ]
    )
    return response["output"]["message"]["content"][0]["text"]

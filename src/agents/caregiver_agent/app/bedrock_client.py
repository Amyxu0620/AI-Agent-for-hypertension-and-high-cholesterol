import json
import anthropic
import os

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
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

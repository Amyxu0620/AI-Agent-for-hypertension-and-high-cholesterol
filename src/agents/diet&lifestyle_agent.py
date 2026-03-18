import anthropic
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "..", "patient_data.json")


# ─────────────────────────────────────────────────────────────
# JSON helpers
# ─────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────
# Claude helper
# ─────────────────────────────────────────────────────────────
def ask_claude(prompt):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not found."

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=700,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"Error generating response: {str(e)}"


# ─────────────────────────────────────────────────────────────
# Food knowledge base
# ─────────────────────────────────────────────────────────────
FOOD_DB = {
    "nasi lemak": {
        "tags": ["high_sodium", "high_fat"],
        "advice": "Better as an occasional choice. Ask for less sambal, avoid fried sides, and keep the portion moderate."
    },
    "chicken rice": {
        "tags": ["moderate_sodium", "moderate_fat"],
        "advice": "Choose steamed or roasted chicken, ask for less sauce, and add vegetables if possible."
    },
    "char kway teow": {
        "tags": ["high_sodium", "high_fat"],
        "advice": "Not ideal as a regular option. A lighter soup-based meal would usually be better."
    },
    "laksa": {
        "tags": ["high_sodium", "high_fat"],
        "advice": "Usually quite rich and salty. Better occasionally than daily."
    },
    "bak chor mee": {
        "tags": ["high_sodium"],
        "advice": "Ask for less sauce and avoid finishing all the soup if there is any."
    },
    "kopi": {
        "tags": ["sugary_if_sweetened"],
        "advice": "Try kopi-o kosong or less sugar versions where possible."
    },
    "fish soup": {
        "tags": ["low_fat", "moderate_sodium"],
        "advice": "A generally better option. Ask for less salt and avoid drinking all the soup."
    },
    "yong tau foo": {
        "tags": ["lower_sodium_option"],
        "advice": "A better choice if you pick more vegetables and tofu, and fewer processed items."
    },
    "caifan": {
        "tags": ["depends_on_choices"],
        "advice": "Try 1 lean protein and 2 vegetable dishes, and avoid gravy and fried items."
    },
    "roti prata": {
        "tags": ["high_fat", "refined_carbs"],
        "advice": "Better as an occasional treat than a regular breakfast."
    },
    "oatmeal": {
        "tags": ["heart_friendly"],
        "advice": "A good option if you avoid too much sugar."
    }
}


CONDITION_RULES = {
    "hypertension": {
        "avoid_tags": {"high_sodium"},
        "watch_tags": {"moderate_sodium"},
        "goal": "lower sodium intake"
    },
    "hyperlipidaemia": {
        "avoid_tags": {"high_fat"},
        "watch_tags": {"moderate_fat"},
        "goal": "lower unhealthy fat intake"
    },
    "high cholesterol": {
        "avoid_tags": {"high_fat"},
        "watch_tags": {"moderate_fat"},
        "goal": "lower unhealthy fat intake"
    },
    "diabetes": {
        "avoid_tags": {"refined_carbs", "sugary_if_sweetened"},
        "watch_tags": set(),
        "goal": "reduce sugar and refined carbohydrate spikes"
    }
}


# ─────────────────────────────────────────────────────────────
# Utility
# ─────────────────────────────────────────────────────────────
def classify_food(food_name):
    return FOOD_DB.get(
        food_name.strip().lower(),
        {
            "tags": ["unknown"],
            "advice": "I do not have an exact match for this food, so I would suggest less oily, less salty, and less processed choices."
        }
    )


def evaluate_food(food_tags, conditions):
    issues = []

    for condition in conditions:
        rules = CONDITION_RULES.get(condition.lower())
        if not rules:
            continue

        tag_set = set(food_tags)

        if tag_set & rules["avoid_tags"]:
            issues.append(f"less suitable for {condition}")
        elif tag_set & rules["watch_tags"]:
            issues.append(f"okay only in moderation for {condition}")

    return issues


def find_food_in_text(text):
    text = text.lower()
    for food in FOOD_DB:
        if food in text:
            return food
    return None


def detect_meal_logging(query):
    q = query.lower()
    patterns = [
        r"i had (.+)",
        r"i ate (.+)",
        r"for lunch i had (.+)",
        r"for dinner i had (.+)",
        r"for breakfast i had (.+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            meal = match.group(1).strip().rstrip(".!?")
            return meal
    return None


def detect_steps_logging(query):
    q = query.lower()
    patterns = [
        r"i walked (\d+)\s*steps",
        r"i did (\d+)\s*steps",
        r"today i walked (\d+)",
        r"i walked (\d+)"
    ]

    for pattern in patterns:
        match = re.search(pattern, q)
        if match:
            return int(match.group(1))
    return None


def log_meal(patient, meal):
    patient.setdefault("meals_today", [])
    patient["meals_today"].append(meal)
    save_patient(patient)


def log_steps(patient, steps):
    patient["steps_today"] = patient.get("steps_today", 0) + int(steps)
    save_patient(patient)


def get_daily_summary(patient):
    risky_count = 0
    for meal in patient.get("meals_today", []):
        meal_info = classify_food(meal)
        tags = set(meal_info["tags"])
        if {"high_sodium", "high_fat", "refined_carbs"} & tags:
            risky_count += 1

    return {
        "patient": patient.get("patient", "Unknown"),
        "conditions": patient.get("conditions", []),
        "meals_today": patient.get("meals_today", []),
        "steps_today": patient.get("steps_today", 0),
        "symptoms_today": patient.get("symptoms_today", []),
        "higher_risk_meals": risky_count
    }


# ─────────────────────────────────────────────────────────────
# Local rule-based responses
# ─────────────────────────────────────────────────────────────
def local_rule_based_response(patient, query):
    conditions = patient.get("conditions", [])
    q = query.lower().strip()

    meal = detect_meal_logging(query)
    if meal:
        log_meal(patient, meal)
        meal_info = classify_food(meal)
        issues = evaluate_food(meal_info["tags"], conditions)

        response = [f"I’ve logged **{meal}** in your meals today."]

        if meal_info["tags"] != ["unknown"]:
            response.append(f"It is tagged as: {', '.join(meal_info['tags'])}.")
        else:
            response.append("I could not classify it exactly, so I’m giving general guidance.")

        if issues:
            response.append("This may be less suitable because it is " + "; ".join(issues) + ".")
        else:
            response.append("This seems reasonably acceptable based on your current conditions.")

        response.append(meal_info["advice"])
        response.append("_This is general lifestyle guidance, not medical advice._")
        return "\n\n".join(response)

    steps = detect_steps_logging(query)
    if steps is not None:
        log_steps(patient, steps)
        total = patient.get("steps_today", 0)

        if total < 3000:
            assessment = "That is a start, but still quite low for the day."
        elif total < 6000:
            assessment = "That is a decent amount of activity."
        elif total < 8000:
            assessment = "That is a good activity level today."
        else:
            assessment = "That is a strong activity level today."

        return (
            f"I’ve logged **{steps} steps**.\n\n"
            f"Your total steps today are now **{total}**. {assessment}"
        )

    if q.startswith("can i eat ") or "okay for me to eat" in q or q.startswith("is "):
        food = find_food_in_text(q)
        if food:
            meal_info = classify_food(food)
            issues = evaluate_food(meal_info["tags"], conditions)

            response = [f"**{food.title()}** is tagged as: {', '.join(meal_info['tags'])}."]

            if issues:
                response.append(
                    f"For your conditions ({', '.join(conditions)}), it is **not the best regular choice** because it is "
                    + "; ".join(issues) + "."
                )
            else:
                response.append("For your current conditions, it can be acceptable in moderation.")

            response.append(meal_info["advice"])
            response.append("_Please follow your doctor or dietitian’s advice for stricter dietary needs._")
            return "\n\n".join(response)

    if "hawker" in q or "what should i eat" in q or "recommend" in q:
        return (
            f"For your conditions ({', '.join(conditions)}), better everyday choices would usually be:\n\n"
            f"- fish soup\n"
            f"- yong tau foo with more vegetables\n"
            f"- caifan with 2 vegetables and 1 lean protein\n"
            f"- oatmeal or eggs for breakfast\n\n"
            "Main idea: less salty, less oily, less fried, and more vegetables."
        )

    return None


# ─────────────────────────────────────────────────────────────
# LLM fallback
# ─────────────────────────────────────────────────────────────
def llm_lifestyle_response(patient, query):
    prompt = f"""
You are a practical diet and lifestyle assistant for an elderly Singaporean patient.

Patient: {patient.get('patient', 'Unknown')}
Conditions: {', '.join(patient.get('conditions', [])) if patient.get('conditions') else 'None'}
Symptoms today: {', '.join(patient.get('symptoms_today', [])) if patient.get('symptoms_today') else 'None'}
Meals today: {', '.join(patient.get('meals_today', [])) if patient.get('meals_today') else 'None'}
Steps today: {patient.get('steps_today', 0)}

The patient asked:
"{query}"

Instructions:
- Answer practical real-life food and lifestyle questions.
- Be useful for Singapore hawker food choices.
- Consider conditions like hypertension, hyperlipidaemia, diabetes.
- Keep the answer short, warm, and practical.
- Do not diagnose.
- Do not recommend medication changes.
- If symptoms are involved, advise discussing them with a doctor.
- Prefer simple suggestions like lower-sodium swaps, less oily choices, and realistic activity advice.

Return:
1. Direct answer
2. Better alternative if relevant
3. Short caution if relevant
"""
    return ask_claude(prompt)


# ─────────────────────────────────────────────────────────────
# Main orchestrator entry
# ─────────────────────────────────────────────────────────────
def handle_user_query(patient, query):
    local_response = local_rule_based_response(patient, query)
    if local_response:
        return local_response
    return llm_lifestyle_response(patient, query)


# ─────────────────────────────────────────────────────────────
# Optional local test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    patient = load_patient()

    test_queries = [
        "Can I eat nasi lemak?",
        "I had chicken rice for lunch",
        "I walked 4000 steps today",
        "What should I eat at the hawker centre?"
    ]

    for q in test_queries:
        print("\nUSER:", q)
        print("AGENT:", handle_user_query(patient, q))

    print("\nUPDATED DAILY SUMMARY:")
    print(get_daily_summary(load_patient()))

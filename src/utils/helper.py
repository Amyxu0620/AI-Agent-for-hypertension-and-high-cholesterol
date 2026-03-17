# This function is for caregiver_agent
def split_emails(raw: str):
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]

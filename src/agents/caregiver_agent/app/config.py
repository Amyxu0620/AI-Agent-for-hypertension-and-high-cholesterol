import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "")
SES_SOURCE_EMAIL = os.getenv("SES_SOURCE_EMAIL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./caregiver.db")
ALERT_FAMILY_AFTER_DAYS = int(os.getenv("ALERT_FAMILY_AFTER_DAYS", "7"))

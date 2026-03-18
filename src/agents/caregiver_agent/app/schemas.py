from pydantic import BaseModel
from typing import Optional


class PatientCreate(BaseModel):
    name: str
    self_dependent: bool = True
    caregiver_email: str
    family_emails: str = ""


class DailyLogCreate(BaseModel):
    patient_id: int
    sleep_hours: float
    calories_intake: float
    nutrition_level: str
    exercise_intensity: str
    calories_burnt: float
    steps: int
    emotional_state: str
    needs_bath: bool = False
    needs_haircut: bool = False
    other_care_needs: str = ""


class HealthMetricCreate(BaseModel):
    patient_id: int
    metric_type: str
    value: float
    unit: str


class VisitLogCreate(BaseModel):
    patient_id: int
    family_member_email: str
    notes: str = ""


class LocationEventCreate(BaseModel):
    patient_id: int
    geofence_type: str   
    event_type: str      


class MessageResponse(BaseModel):
    message: str

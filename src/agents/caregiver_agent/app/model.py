from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    self_dependent = Column(Boolean, default=True)

    caregiver_email = Column(String, nullable=False)
    family_emails = Column(Text, default="")  # comma-separated for prototype use

    daily_logs = relationship("DailyLog", back_populates="patient", cascade="all, delete-orphan")
    metrics = relationship("HealthMetric", back_populates="patient", cascade="all, delete-orphan")
    visits = relationship("VisitLog", back_populates="patient", cascade="all, delete-orphan")
    alerts = relationship("AlertLog", back_populates="patient", cascade="all, delete-orphan")


class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    sleep_hours = Column(Float, default=0)
    calories_intake = Column(Float, default=0)
    nutrition_level = Column(String, default="")
    exercise_intensity = Column(String, default="")
    calories_burnt = Column(Float, default=0)
    steps = Column(Integer, default=0)
    emotional_state = Column(String, default="")

    # only included because you explicitly wanted it when patient is not self-dependent
    needs_bath = Column(Boolean, default=False)
    needs_haircut = Column(Boolean, default=False)
    other_care_needs = Column(String, default="")

    log_date = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="daily_logs")


class HealthMetric(Base):
    __tablename__ = "health_metrics"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    metric_type = Column(String, nullable=False)   # systolic_bp, diastolic_bp, resting_hr, sleep_hours, steps, etc.
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="metrics")


class VisitLog(Base):
    __tablename__ = "visit_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    family_member_email = Column(String, nullable=False)
    visited_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String, default="")

    patient = relationship("Patient", back_populates="visits")


class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)

    severity = Column(String, nullable=False)   # info / caution / urgent
    alert_type = Column(String, nullable=False) # risk / location / family / summary
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="alerts")

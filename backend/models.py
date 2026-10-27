# backend/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from .database import Base
import datetime


class TrainSnapshot(Base):
    __tablename__ = "train_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    train_id = Column(String, index=True)

    cert_rolling = Column(DateTime, nullable=True)
    cert_signalling = Column(DateTime, nullable=True)
    cert_telecom = Column(DateTime, nullable=True)

    jobcard_severity = Column(Integer, default=0)
    pred_fail = Column(Float, default=0.0)

    branding_req_hours = Column(Integer, default=0)
    branding_done = Column(Integer, default=0)
    branding_shortfall = Column(Integer, default=0)

    advertiser = Column(String, nullable=True)
    advertiser_total_shortfall = Column(Integer, default=0)
    advertiser_sla_risk = Column(Boolean, default=False)

    odometer_km = Column(Integer, default=0)
    last_clean_days = Column(Integer, default=0)
    stabling_index = Column(Integer, default=0)
    vibration = Column(Float, default=0.0)
    temp = Column(Float, default=0.0)
    humidity = Column(Float, default=0.0)
    manual_blocked = Column(Boolean, default=False)  # operator override
    raw = Column(JSON, nullable=True)  # store original raw ingestion row as JSON

# keep other classes (Inductio
class InductionPlan(Base):
    __tablename__ = "induction_plans"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    service_count = Column(Integer, default=0)
    lambda_risk = Column(Float, default=1.5)
    use_ml = Column(Boolean, default=True)
    summary = Column(JSON, nullable=True)   # summary counts
    plan_json = Column(JSON, nullable=True) # full plan results rows

class JobCard(Base):
    __tablename__ = "jobcards"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(String, index=True)
    severity = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class BrandingContract(Base):
    __tablename__ = "branding_contracts"
    id = Column(Integer, primary_key=True, index=True)
    train_id = Column(String, index=True)
    required_hours = Column(Integer, default=0)
    done_hours = Column(Integer, default=0)
    advertiser = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

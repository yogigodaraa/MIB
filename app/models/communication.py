"""
Communication and Alert Models
Pydantic models for crew communication, alerts, and responses.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CrewMember(BaseModel):
    """Crew member information and contact details"""
    id: str
    name: str
    role: str  # "deck_officer", "bosun", "engineer", "captain"
    phone: Optional[str] = None
    radio_channel: Optional[str] = None
    location: Optional[str] = None
    status: str = "available"  # "available", "responding", "busy", "off_duty"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AlertResponse(BaseModel):
    """Response from crew member to an alert"""
    alert_id: str
    crew_member_id: str
    response_type: str  # "acknowledged", "responding", "resolved", "escalated"
    message: Optional[str] = None
    timestamp: datetime
    location: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CommunicationMessage(BaseModel):
    """Communication message sent to crew"""
    id: str
    message_type: str  # "sms", "push", "radio", "manual"
    recipient: str
    content: str
    priority: str  # "low", "medium", "high", "critical"
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    status: str = "pending"  # "pending", "sent", "delivered", "acknowledged", "failed"
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ManualDataEntry(BaseModel):
    """Manual data entry when sensors fail"""
    hook_id: str
    tension_value: int
    entered_by: str
    reason: str  # "sensor_fault", "calibration", "verification"
    timestamp: datetime
    confidence: float = 0.8  # Lower confidence for manual entries
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Alert(BaseModel):
    """Alert for tension or system issues"""
    id: str
    hook_id: str
    berth: str
    bollard: str
    hook: str
    level: str  # "low", "medium", "high", "critical"
    raw_tension: Optional[int] = None
    processed_tension: Optional[int] = None
    timestamp: datetime
    faulted: bool = False
    attached_line: Optional[str] = None
    confidence_score: float = 1.0
    quality_flags: List[str] = []
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
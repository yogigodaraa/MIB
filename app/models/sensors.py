"""
Sensor Data Models
Pydantic models for sensor readings and monitoring equipment.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
from datetime import datetime


class RadarData(BaseModel):
    """Radar sensor data for distance monitoring"""
    name: str
    shipDistance: Optional[float] = None
    distanceChange: Optional[float] = None
    distanceStatus: str = "INACTIVE"
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 2) if v is not None else None
        }


class HookData(BaseModel):
    """Hook tension sensor data with enhanced accuracy fields"""
    name: str
    tension: Optional[int] = None
    faulted: bool = False
    attachedLine: Optional[str] = None
    
    # Enhanced accuracy fields
    sensor_quality: Optional[str] = Field(default="good", pattern="^(excellent|good|fair|poor)$")
    calibration_date: Optional[datetime] = None
    environmental_factors: Optional[Dict[str, Union[str, float]]] = {}
    load_history: Optional[List[int]] = []
    confidence_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    last_maintenance: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
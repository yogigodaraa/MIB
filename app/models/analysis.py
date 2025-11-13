"""
Analysis and Monitoring Models
Pydantic models for movement analysis and monitoring results.
"""

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class MovementVector(BaseModel):
    """3D movement vector for ship positioning"""
    dx: float = 0.0      # X movement (forward/back)
    dy: float = 0.0      # Y movement (left/right)  
    dz: float = 0.0      # Z movement (up/down)
    speed: float = 0.0   # Overall speed
    direction: str = 'stable'
    confidence: float = 0.0
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 3) if v is not None else None
        }


class Position3D(BaseModel):
    """3D position coordinates"""
    x: float = 0.0  # Forward/Backward (negative = towards bow)
    y: float = 0.0  # Left/Right (negative = port, positive = starboard)
    z: float = 0.0  # Up/Down (positive = up)
    distance: float = 0.0  # Overall distance from berth
    confidence: float = 0.0
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 3) if v is not None else None
        }


class MovementAnalysis(BaseModel):
    """Analysis of movement patterns"""
    pattern: str = 'stable'
    oscillation: bool = False
    drift_direction: Optional[str] = None
    stability_score: int = 85
    risk_assessment: str = 'low'
    movement_intensity: str = 'minimal'


class MovementPrediction(BaseModel):
    """Prediction of future movement"""
    predicted_position: Position3D
    time_horizon: str = '2_minutes'
    confidence: float = 0.5
    warnings: List[str] = []
    recommendations: List[str] = []


class ShipMovement(BaseModel):
    """Complete ship movement data"""
    berth_name: str
    ship_name: str
    current_position: Position3D
    movement_vector: MovementVector
    movement_analysis: MovementAnalysis
    movement_prediction: MovementPrediction
    timestamp: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TensionPrediction(BaseModel):
    """Tension trend prediction"""
    trend: str = 'stable'
    slope: float = 0.0
    current: float = 0.0
    predicted_5min: float = 0.0
    confidence: float = 0.7
    time_to_critical: Optional[float] = None
    
    class Config:
        json_encoders = {
            float: lambda v: round(v, 3) if v is not None else None
        }
"""
Ship Data Models
Pydantic models for ship-related data structures.
"""

from pydantic import BaseModel
from typing import Optional


class ShipData(BaseModel):
    """Basic ship information"""
    name: str
    vesselId: str
    
    class Config:
        json_encoders = {
            # Add custom encoders if needed
        }
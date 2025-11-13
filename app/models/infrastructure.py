"""
Infrastructure Data Models
Pydantic models for berths, bollards, and port infrastructure.
"""

from pydantic import BaseModel
from typing import List
from .ship import ShipData
from .sensors import RadarData, HookData


class BollardData(BaseModel):
    """Bollard with attached hooks"""
    name: str
    hooks: List[HookData] = []
    
    @property
    def hook_count(self) -> int:
        """Get total number of hooks on this bollard"""
        return len(self.hooks)
    
    @property
    def active_hooks(self) -> List[HookData]:
        """Get hooks that are not faulted"""
        return [hook for hook in self.hooks if not hook.faulted]


class BerthData(BaseModel):
    """Berth with all associated infrastructure and monitoring equipment"""
    name: str
    bollardCount: int
    hookCount: int
    ship: ShipData
    radars: List[RadarData] = []
    bollards: List[BollardData] = []
    
    @property
    def total_hooks(self) -> int:
        """Calculate total hooks across all bollards"""
        return sum(bollard.hook_count for bollard in self.bollards)
    
    @property
    def active_radars(self) -> List[RadarData]:
        """Get radars that are active"""
        return [radar for radar in self.radars if radar.distanceStatus == "ACTIVE"]


class PortData(BaseModel):
    """Complete port data with all berths"""
    name: str
    berths: List[BerthData] = []
    
    @property
    def total_berths(self) -> int:
        """Get total number of berths"""
        return len(self.berths)
    
    @property
    def occupied_berths(self) -> List[BerthData]:
        """Get berths that have ships"""
        return [berth for berth in self.berths if berth.ship.name != ""]
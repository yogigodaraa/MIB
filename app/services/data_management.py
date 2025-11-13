"""
Data Management Service
Service for managing incoming data, storage, and processing.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..models import PortData, BerthData


class DataManagementService:
    """Service for managing incoming data and storage"""
    
    def __init__(self):
        self.latest_data: Optional[Dict] = None
        self.data_history: List[Dict] = []
        self.tension_history: Dict[str, List[Dict]] = {}
        
        # Configuration
        self.config = {
            'max_history_entries': 100,
            'max_tension_history': 50,
            'data_retention_hours': 24
        }
    
    def receive_port_data(self, data: PortData) -> Dict[str, Any]:
        """Receive and store port data"""
        # Store the data
        self.latest_data = data.dict()
        
        timestamp = datetime.now()
        self.data_history.append({
            "timestamp": timestamp.isoformat(),
            "data": self.latest_data
        })
        
        # Keep only recent entries
        if len(self.data_history) > self.config['max_history_entries']:
            self.data_history = self.data_history[-self.config['max_history_entries']:]
        
        # Process tension data for history tracking
        self._process_tension_data(data.berths, timestamp)
        
        return {
            "status": "received",
            "timestamp": timestamp.isoformat(),
            "berths_count": len(data.berths),
            "port_name": data.name
        }
    
    def _process_tension_data(self, berths: List[BerthData], timestamp: datetime):
        """Process and store tension data for trending"""
        for berth in berths:
            for bollard in berth.bollards:
                for hook in bollard.hooks:
                    if hook.tension is not None:
                        hook_id = f"{berth.name}-{bollard.name}-{hook.name}"
                        
                        if hook_id not in self.tension_history:
                            self.tension_history[hook_id] = []
                        
                        self.tension_history[hook_id].append({
                            'timestamp': timestamp.isoformat(),
                            'tension': hook.tension,
                            'faulted': hook.faulted,
                            'confidence': hook.confidence_score or 1.0,
                            'sensor_quality': hook.sensor_quality or 'good'
                        })
                        
                        # Keep only recent readings
                        if len(self.tension_history[hook_id]) > self.config['max_tension_history']:
                            self.tension_history[hook_id] = self.tension_history[hook_id][-self.config['max_tension_history']:]
    
    def get_latest_data(self) -> Optional[Dict]:
        """Get the latest received data"""
        return self.latest_data
    
    def get_data_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get data history with optional limit"""
        if limit:
            return self.data_history[-limit:]
        return self.data_history
    
    def get_tension_history(self, hook_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get tension history for a specific hook"""
        history = self.tension_history.get(hook_id, [])
        if limit:
            return history[-limit:]
        return history
    
    def get_all_tension_history(self) -> Dict[str, List[Dict]]:
        """Get tension history for all hooks"""
        return self.tension_history
    
    def convert_to_serializable(self, obj: Any) -> Any:
        """Convert datetime objects to strings for JSON serialization"""
        if isinstance(obj, dict):
            return {key: self.convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.convert_to_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj
    
    def cleanup_old_data(self):
        """Clean up old data based on retention policy"""
        cutoff_time = datetime.now() - timedelta(hours=self.config['data_retention_hours'])
        
        # Clean up data history
        self.data_history = [
            entry for entry in self.data_history
            if datetime.fromisoformat(entry['timestamp']) > cutoff_time
        ]
        
        # Clean up tension history
        for hook_id in list(self.tension_history.keys()):
            self.tension_history[hook_id] = [
                entry for entry in self.tension_history[hook_id]
                if datetime.fromisoformat(entry['timestamp']) > cutoff_time
            ]
            
            # Remove empty entries
            if not self.tension_history[hook_id]:
                del self.tension_history[hook_id]
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        stats = {
            'total_data_entries': len(self.data_history),
            'total_hooks_tracked': len(self.tension_history),
            'data_age_hours': 0,
            'tension_readings_total': sum(len(history) for history in self.tension_history.values()),
            'last_updated': None
        }
        
        if self.data_history:
            latest_timestamp = datetime.fromisoformat(self.data_history[-1]['timestamp'])
            stats['data_age_hours'] = (datetime.now() - latest_timestamp).total_seconds() / 3600
            stats['last_updated'] = latest_timestamp.isoformat()
        
        return stats
    
    def find_hook_by_id(self, hook_id: str) -> Optional[Dict]:
        """Find hook information by ID in the latest data"""
        if not self.latest_data or 'berths' not in self.latest_data:
            return None
        
        for berth in self.latest_data['berths']:
            for bollard in berth.get('bollards', []):
                for hook in bollard.get('hooks', []):
                    current_id = f"{berth['name']}-{bollard['name']}-{hook['name']}"
                    if current_id == hook_id:
                        return {
                            'hook': hook,
                            'bollard': bollard['name'],
                            'berth': berth['name'],
                            'ship': berth['ship']['name']
                        }
        return None
    
    def get_berth_data(self, berth_name: str) -> Optional[Dict]:
        """Get data for a specific berth"""
        if not self.latest_data or 'berths' not in self.latest_data:
            return None
        
        for berth in self.latest_data['berths']:
            if berth['name'] == berth_name:
                return berth
        
        return None
    
    def get_hooks_by_berth(self, berth_name: str) -> List[Dict]:
        """Get all hooks for a specific berth"""
        berth_data = self.get_berth_data(berth_name)
        if not berth_data:
            return []
        
        hooks = []
        for bollard in berth_data.get('bollards', []):
            for hook in bollard.get('hooks', []):
                hook_info = {
                    'id': f"{berth_name}-{bollard['name']}-{hook['name']}",
                    'hook': hook,
                    'bollard': bollard['name'],
                    'berth': berth_name
                }
                hooks.append(hook_info)
        
        return hooks
    
    def add_manual_tension_entry(self, hook_id: str, tension_value: int, crew_id: str, reason: str):
        """Add manual tension entry to history"""
        timestamp = datetime.now()
        
        if hook_id not in self.tension_history:
            self.tension_history[hook_id] = []
        
        self.tension_history[hook_id].append({
            'timestamp': timestamp.isoformat(),
            'tension': tension_value,
            'manual': True,
            'entered_by': crew_id,
            'reason': reason,
            'confidence': 0.8  # Lower confidence for manual entries
        })
        
        # Keep only recent readings
        if len(self.tension_history[hook_id]) > self.config['max_tension_history']:
            self.tension_history[hook_id] = self.tension_history[hook_id][-self.config['max_tension_history']:]
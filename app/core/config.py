"""
Application Configuration
Central configuration management for the BHP Mooring Data Dashboard.
"""

from pydantic_settings import BaseSettings
from typing import Dict, Any, Optional
import os


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application settings
    app_name: str = "BHP Mooring Data Dashboard"
    version: str = "1.0.0"
    debug: bool = False
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False
    
    # Database/Storage settings
    data_retention_hours: int = 24
    max_history_entries: int = 100
    max_tension_history: int = 50
    
    # Monitoring settings
    alert_thresholds: Dict[str, int] = {
        "low": 30,
        "medium": 70,
        "high": 85,
        "critical": 95
    }
    
    # Tension monitoring configuration
    tension_config: Dict[str, Any] = {
        "buffer_size": 50,
        "outlier_threshold": 2.5,
        "confidence_threshold": 0.7,
        "calibration_drift_limit": 5,
        "smoothing_window": 5,
        "prediction_window": 10
    }
    
    # Communication settings
    sms_enabled: bool = False
    push_notifications_enabled: bool = True
    radio_enabled: bool = False
    
    # Security settings
    api_key: Optional[str] = None
    cors_origins: list = ["*"]
    
    # Logging settings
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    # Template settings
    template_directory: str = "templates"
    static_directory: str = "static"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


def update_settings(**kwargs):
    """Update settings with new values"""
    for key, value in kwargs.items():
        if hasattr(settings, key):
            setattr(settings, key, value)


# Alert level configurations
ALERT_LEVELS = {
    'safe': {
        'priority': 0,
        'color': '#28a745',  # Green
        'description': 'Normal operation'
    },
    'low': {
        'priority': 1,
        'color': '#ffc107',  # Yellow
        'description': 'Minor attention needed'
    },
    'medium': {
        'priority': 2,
        'color': '#fd7e14',  # Orange
        'description': 'Moderate concern'
    },
    'high': {
        'priority': 3,
        'color': '#dc3545',  # Red
        'description': 'High priority action needed'
    },
    'critical': {
        'priority': 4,
        'color': '#6f42c1',  # Purple
        'description': 'Critical immediate action required'
    }
}


# Communication priority levels
COMMUNICATION_PRIORITY = {
    'low': {
        'channels': ['push'],
        'delay_seconds': 30,
        'retry_attempts': 1
    },
    'medium': {
        'channels': ['sms', 'push'],
        'delay_seconds': 10,
        'retry_attempts': 2
    },
    'high': {
        'channels': ['sms', 'push'],
        'delay_seconds': 5,
        'retry_attempts': 3
    },
    'critical': {
        'channels': ['radio', 'sms', 'push'],
        'delay_seconds': 0,
        'retry_attempts': 5
    }
}


# Crew roles and permissions
CREW_ROLES = {
    'captain': {
        'name': 'Captain',
        'permissions': ['all'],
        'priority': 1,
        'radio_channel': 'bridge'
    },
    'deck_officer': {
        'name': 'Deck Officer',
        'permissions': ['monitoring', 'alerts', 'manual_entry'],
        'priority': 2,
        'radio_channel': 'bridge'
    },
    'bosun': {
        'name': 'Bosun',
        'permissions': ['monitoring', 'alerts', 'manual_entry'],
        'priority': 3,
        'radio_channel': 'deck'
    },
    'able_seaman': {
        'name': 'Able Seaman',
        'permissions': ['monitoring'],
        'priority': 4,
        'radio_channel': 'deck'
    },
    'engineer': {
        'name': 'Engineer',
        'permissions': ['monitoring', 'maintenance'],
        'priority': 3,
        'radio_channel': 'engine'
    }
}


def get_alert_config(level: str) -> Dict[str, Any]:
    """Get alert configuration for a specific level"""
    return ALERT_LEVELS.get(level, ALERT_LEVELS['safe'])


def get_communication_config(priority: str) -> Dict[str, Any]:
    """Get communication configuration for a priority level"""
    return COMMUNICATION_PRIORITY.get(priority, COMMUNICATION_PRIORITY['low'])


def get_crew_role_config(role: str) -> Dict[str, Any]:
    """Get crew role configuration"""
    return CREW_ROLES.get(role, CREW_ROLES['able_seaman'])
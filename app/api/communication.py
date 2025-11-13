"""
Communication API Routes
API endpoints for crew communication, alerts, and manual operations.
"""

from fastapi import APIRouter
from datetime import datetime
from typing import List

from ..services import CommunicationService, DataManagementService
from ..models import Alert

router = APIRouter(prefix="/api")

# Service instances (will be injected in main.py)
communication_service: CommunicationService = None
data_service: DataManagementService = None


def init_services(comm_svc, data_svc):
    """Initialize service dependencies"""
    global communication_service, data_service
    communication_service = comm_svc
    data_service = data_svc


@router.get("/crew-status")
async def get_crew_status():
    """Get current crew status and assignments"""
    return communication_service.get_crew_status_summary()


@router.post("/crew-response")
async def record_crew_response(alert_id: str, crew_id: str, response_type: str, message: str = None):
    """Record crew response to an alert"""
    response = communication_service.process_crew_response(alert_id, crew_id, response_type, message)
    return {"status": "recorded", "response": response.dict()}


@router.get("/communication-log")
async def get_communication_log(limit: int = 50):
    """Get recent communication log"""
    communications = communication_service.get_communication_log(limit)
    return {
        "communications": [comm.dict() for comm in communications],
        "total_count": len(communications),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/active-alerts")
async def get_active_alerts():
    """Get all active alerts with their status"""
    active_alerts = communication_service.get_active_alerts()
    return {
        "active_alerts": active_alerts,
        "total_active": len(active_alerts),
        "timestamp": datetime.now().isoformat()
    }


@router.post("/manual-data-entry")
async def submit_manual_data(hook_id: str, tension_value: int, crew_id: str, reason: str):
    """Submit manual tension data when sensors fail"""
    
    # Validate input
    if not (0 <= tension_value <= 100):
        return {"error": "Tension value must be between 0 and 100"}
    
    # Record manual entry
    entry = communication_service.record_manual_data_entry(hook_id, tension_value, crew_id, reason)
    
    # Also add to data service for tracking
    data_service.add_manual_tension_entry(hook_id, tension_value, crew_id, reason)
    
    return {"status": "recorded", "entry": entry.dict()}


@router.post("/broadcast-alert")
async def broadcast_custom_alert(message: str, priority: str = "medium", channels: List[str] = None):
    """Broadcast custom alert message to crew"""
    
    if channels is None:
        channels = ["sms", "push"]
    
    message_ids = await communication_service.broadcast_custom_alert(message, priority, channels)
    
    return {
        "status": "broadcasted",
        "message_ids": message_ids,
        "channels_used": channels,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/crew-briefing")
async def get_crew_briefing():
    """Get formatted briefing for crew shift change"""
    latest_data = data_service.get_latest_data()
    
    if not latest_data:
        return {"error": "No data available"}
    
    # Generate briefing summary
    summary = generate_hook_status_summary(latest_data)
    
    briefing = {
        'shift_summary': f"Overall Status: {summary['overall_status'].title()}",
        'immediate_actions': summary['priority_actions'],
        'berth_status': {},
        'watch_points': [],
        'maintenance_needed': [],
        'communication_protocol': summary['communication_level'],
        'statistics': {
            'total_hooks': summary['total_hooks'],
            'problematic_hooks': summary['problematic_hooks'],
            'critical_hooks': summary['critical_hooks']
        }
    }
    
    for berth_name, berth_data in summary['hook_groups'].items():
        briefing['berth_status'][berth_name] = {
            'ship': berth_data['ship'],
            'status': berth_data['status'],
            'hook_count': len(berth_data['hooks']),
            'issues': [h for h in berth_data['hooks'] if h['alert_level'] not in ['safe', 'unknown']],
            'validation': berth_data['validation']
        }
        
        # Add watch points
        for hook in berth_data['hooks']:
            if hook['communication_priority'] in ['high', 'critical']:
                briefing['watch_points'].append(hook['crew_message'])
            if hook['faulted']:
                briefing['maintenance_needed'].append(f"Replace sensor: {hook['location']}")
            if hook.get('sensor_quality') == 'poor':
                briefing['maintenance_needed'].append(f"Recalibrate sensor: {hook['location']}")
    
    return briefing


def generate_hook_status_summary(latest_data: dict) -> dict:
    """Generate summary of hook statuses for briefing"""
    summary = {
        'overall_status': 'safe',
        'priority_actions': [],
        'hook_groups': {},
        'communication_level': 'normal',
        'total_hooks': 0,
        'problematic_hooks': 0,
        'critical_hooks': 0
    }
    
    if not latest_data or 'berths' not in latest_data:
        return summary
    
    for berth in latest_data['berths']:
        berth_summary = {
            'name': berth['name'],
            'ship': berth['ship']['name'],
            'hooks': [],
            'status': 'safe',
            'validation': {'status': 'ok', 'confidence': 1.0}
        }
        
        for bollard in berth.get('bollards', []):
            if not bollard:
                continue
            for hook in bollard.get('hooks', []):
                if not hook:
                    continue
                summary['total_hooks'] += 1
                
                tension = hook.get('tension', 0)
                if tension is None:
                    tension = 0
                faulted = hook.get('faulted', False)
                
                # Determine alert level
                alert_level = 'safe'
                if tension >= 95:
                    alert_level = 'critical'
                elif tension >= 85:
                    alert_level = 'high'
                elif tension >= 70:
                    alert_level = 'medium'
                elif tension >= 30:
                    alert_level = 'low'
                
                # Get safe names for location string
                berth_name = berth.get('name', 'Unknown') if berth else 'Unknown'
                bollard_name = bollard.get('name', 'Unknown') if bollard else 'Unknown'
                hook_name = hook.get('name', 'Unknown') if hook else 'Unknown'
                
                hook_status = {
                    'location': f"{berth_name}-{bollard_name}-{hook_name}",
                    'tension': tension,
                    'alert_level': alert_level,
                    'faulted': faulted,
                    'communication_priority': 'low',
                    'crew_message': None
                }
                
                if faulted:
                    hook_status['communication_priority'] = 'high'
                    hook_status['crew_message'] = f"Sensor fault at {hook_status['location']} - verify manually"
                elif tension >= 95:
                    hook_status['communication_priority'] = 'critical'
                    hook_status['crew_message'] = f"CRITICAL tension at {hook_status['location']} - release immediately"
                elif tension >= 85:
                    hook_status['communication_priority'] = 'high'
                    hook_status['crew_message'] = f"High tension at {hook_status['location']} - prepare for adjustment"
                
                if alert_level in ['high', 'critical']:
                    summary['problematic_hooks'] += 1
                    if alert_level == 'critical':
                        summary['critical_hooks'] += 1
                
                berth_summary['hooks'].append(hook_status)
        
        # Determine berth status
        if summary['critical_hooks'] > 0:
            berth_summary['status'] = 'critical'
        elif summary['problematic_hooks'] > 0:
            berth_summary['status'] = 'warning'
        
        summary['hook_groups'][berth['name']] = berth_summary
    
    # Generate priority actions
    if summary['critical_hooks'] > 0:
        summary['overall_status'] = 'critical'
        summary['communication_level'] = 'emergency'
        summary['priority_actions'].append(f"🚨 IMMEDIATE: {summary['critical_hooks']} hooks in critical state")
    elif summary['problematic_hooks'] > 0:
        summary['overall_status'] = 'warning'
        summary['communication_level'] = 'urgent'
        summary['priority_actions'].append(f"⚠️ ATTENTION: {summary['problematic_hooks']} hooks need monitoring")
    
    return summary
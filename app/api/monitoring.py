"""
Monitoring API Routes
API endpoints for tension monitoring, alerts, and analysis.
"""

from fastapi import APIRouter
from datetime import datetime
from typing import List, Optional

from ..services import TensionMonitoringService, DataManagementService
from ..models import Alert
from ..utils.helpers import get_alert_priority

router = APIRouter(prefix="/api")

# Service instances (will be injected in main.py)
tension_service: TensionMonitoringService = None
data_service: DataManagementService = None


def init_services(tension_svc, data_svc):
    """Initialize service dependencies"""
    global tension_service, data_service
    tension_service = tension_svc
    data_service = data_svc


def generate_tension_alerts() -> List[dict]:
    """Generate tension alerts from current data"""
    alerts = []
    latest_data = data_service.get_latest_data()
    
    if not latest_data or 'berths' not in latest_data:
        return alerts
    
    for berth in latest_data['berths']:
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                if hook.get('tension') is not None:
                    tension = hook['tension']
                    hook_id = f"{berth['name']}-{bollard['name']}-{hook['name']}"
                    
                    # Get alert level from tension service
                    alert_level = tension_service.get_alert_level(tension)
                    
                    if alert_level != 'safe':
                        # Get prediction from tension service
                        prediction = tension_service.predict_tension_trend(hook_id)
                        
                        alert_data = {
                            'id': hook_id,
                            'berth': berth['name'],
                            'bollard': bollard['name'],
                            'hook': hook['name'],
                            'tension': tension,
                            'level': alert_level,
                            'prediction': prediction.dict() if prediction else None,
                            'timestamp': datetime.now().isoformat(),
                            'faulted': hook.get('faulted', False),
                            'attached_line': hook.get('attachedLine'),
                            'confidence_score': hook.get('confidence_score', 1.0)
                        }
                        alerts.append(alert_data)
    
    return sorted(alerts, key=lambda x: get_alert_priority(x['level']), reverse=True)


@router.get("/alerts")
async def get_current_alerts():
    """API endpoint to get current tension alerts"""
    alerts = generate_tension_alerts()
    return {"alerts": alerts, "timestamp": datetime.now().isoformat()}


@router.get("/enhanced-tension/{hook_id}")
async def get_enhanced_tension_data(hook_id: str):
    """Get detailed enhanced tension data for a specific hook"""
    tension_history = data_service.get_tension_history(hook_id, 20)
    
    if not tension_history:
        return {"error": "No data available for this hook"}
    
    # Get accuracy summary from tension service
    accuracy_summary = tension_service.get_accuracy_summary()
    
    return {
        "hook_id": hook_id,
        "recent_readings": tension_history,
        "accuracy_summary": accuracy_summary,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/system-accuracy-status")
async def get_system_accuracy_status():
    """Get overall system accuracy and sensor health status"""
    accuracy_summary = tension_service.get_accuracy_summary()
    tension_history = data_service.get_all_tension_history()
    
    # Calculate system health metrics
    total_hooks = len(tension_history)
    active_hooks = 0
    outlier_hooks = 0
    low_confidence_hooks = 0
    
    for hook_id, history in tension_history.items():
        if history:
            active_hooks += 1
            latest = history[-1]
            
            if latest.get('is_outlier', False):
                outlier_hooks += 1
            
            if latest.get('confidence', 0) < 0.5:
                low_confidence_hooks += 1
    
    system_health = {
        "total_hooks": total_hooks,
        "active_hooks": active_hooks,
        "outlier_hooks": outlier_hooks,
        "low_confidence_hooks": low_confidence_hooks,
        "system_accuracy": accuracy_summary.get('overall_system_confidence', 0.8),
        "status": "healthy" if accuracy_summary.get('overall_system_confidence', 0.8) > 0.7 else "degraded",
        "recommendations": generate_system_accuracy_recommendations(accuracy_summary)
    }
    
    return {
        "system_health": system_health,
        "accuracy_details": accuracy_summary,
        "timestamp": datetime.now().isoformat()
    }


def generate_system_accuracy_recommendations(accuracy_summary: dict) -> List[str]:
    """Generate recommendations for improving system accuracy"""
    recommendations = []
    
    if accuracy_summary.get('low_confidence_sensors', 0) > 0:
        recommendations.append(f"📊 {accuracy_summary['low_confidence_sensors']} sensors need attention")
    
    if accuracy_summary.get('overall_system_confidence', 0.8) < 0.6:
        recommendations.append("🔧 System accuracy below acceptable threshold - schedule maintenance")
    
    if len(accuracy_summary.get('sensors_needing_attention', [])) > 0:
        recommendations.append("⚠️ Multiple sensors requiring calibration or replacement")
    
    if not recommendations:
        recommendations.append("✅ System accuracy is within acceptable parameters")
    
    return recommendations


@router.get("/system-health")
async def get_system_health():
    """Get overall system health and sensor status"""
    latest_data = data_service.get_latest_data()
    
    if not latest_data:
        return {"status": "no_data", "health": 0.0}
    
    total_hooks = 0
    healthy_hooks = 0
    sensor_issues = []
    
    for berth in latest_data.get('berths', []):
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                total_hooks += 1
                
                # Check sensor health
                if not hook.get('faulted', False):
                    sensor_quality = hook.get('sensor_quality', 'good')
                    confidence = hook.get('confidence_score', 1.0)
                    
                    if sensor_quality in ['excellent', 'good'] and confidence >= 0.8:
                        healthy_hooks += 1
                    else:
                        sensor_issues.append({
                            'location': f"{berth['name']}-{bollard['name']}-{hook['name']}",
                            'issue': f"Quality: {sensor_quality}, Confidence: {confidence:.2f}"
                        })
                else:
                    sensor_issues.append({
                        'location': f"{berth['name']}-{bollard['name']}-{hook['name']}",
                        'issue': "Sensor fault detected"
                    })
    
    health_percentage = (healthy_hooks / total_hooks) * 100 if total_hooks > 0 else 0
    
    return {
        'status': 'healthy' if health_percentage >= 80 else 'degraded' if health_percentage >= 60 else 'poor',
        'health_percentage': round(health_percentage, 1),
        'total_hooks': total_hooks,
        'healthy_hooks': healthy_hooks,
        'sensor_issues': sensor_issues,
        'timestamp': datetime.now().isoformat()
    }


@router.get("/hook-communication/{hook_id}")
async def get_hook_communication_info(hook_id: str):
    """Get detailed communication info for specific hook"""
    hook_info = data_service.find_hook_by_id(hook_id)
    if not hook_info:
        return {"error": "Hook not found"}
    
    tension_history = data_service.get_tension_history(hook_id, 10)
    prediction = tension_service.predict_tension_trend(hook_id)
    
    return {
        'hook_id': hook_id,
        'hook_info': hook_info,
        'recent_history': tension_history,
        'prediction': prediction.dict() if prediction else None,
        'timestamp': datetime.now().isoformat()
    }
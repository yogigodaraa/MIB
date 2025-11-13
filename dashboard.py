#!/usr/bin/env python3
"""
Mooring Data Dashboard
A FastAPI web dashboard to visualize incoming mooring data in real-time.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict
import json
from datetime import datetime, timedelta
import uvicorn
import random
import math
import statistics

app = FastAPI(title="Mooring Data Dashboard")
templates = Jinja2Templates(directory="templates")

def get_tension_class(tension):
    """Helper function to get CSS class based on tension level"""
    if tension >= alert_thresholds['critical']:
        return 'critical'
    elif tension >= alert_thresholds['high']:
        return 'high'  
    elif tension >= alert_thresholds['medium']:
        return 'medium'
    elif tension >= alert_thresholds['low']:
        return 'low'
    else:
        return 'safe'

# Add helper function to template globals
templates.env.globals['get_tension_class'] = get_tension_class

# Store the latest received data
latest_data = {}
data_history = []
tension_history = {}  # Store tension data over time for predictive analytics
alert_thresholds = {
    "low": 30,
    "medium": 70,
    "high": 85,
    "critical": 95
}

# Pydantic models based on the observed data structure
class ShipData(BaseModel):
    name: str
    vesselId: str

class RadarData(BaseModel):
    name: str
    shipDistance: Optional[float]
    distanceChange: Optional[float]
    distanceStatus: str

class HookData(BaseModel):
    name: str
    tension: Optional[int]
    faulted: bool
    attachedLine: Optional[str]
    # Enhanced accuracy fields
    sensor_quality: Optional[str] = Field(default="good", pattern="^(excellent|good|fair|poor)$")
    calibration_date: Optional[datetime] = None
    environmental_factors: Optional[Dict[str, Union[str, float]]] = {}
    load_history: Optional[List[int]] = []
    confidence_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    last_maintenance: Optional[datetime] = None

class BollardData(BaseModel):
    name: str
    hooks: List[HookData]

class BerthData(BaseModel):
    name: str
    bollardCount: int
    hookCount: int
    ship: ShipData
    radars: List[RadarData]
    bollards: List[BollardData]

class PortData(BaseModel):
    name: str
    berths: List[BerthData]

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "latest_data": latest_data,
        "data_count": len(data_history),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Real-time tension monitoring page"""
    alerts = generate_tension_alerts()
    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "latest_data": latest_data,
        "alerts": alerts,
        "tension_history": tension_history,
        "thresholds": alert_thresholds,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

def generate_tension_alerts():
    """Generate tension alerts based on current data and predictions"""
    alerts = []
    if not latest_data or 'berths' not in latest_data:
        return alerts
    
    for berth in latest_data['berths']:
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                if hook.get('tension') is not None:
                    tension = hook['tension']
                    hook_id = f"{berth['name']}-{bollard['name']}-{hook['name']}"
                    
                    # Store tension history for predictions
                    if hook_id not in tension_history:
                        tension_history[hook_id] = []
                    
                    tension_history[hook_id].append({
                        'timestamp': datetime.now().isoformat(),
                        'tension': tension
                    })
                    
                    # Keep only last 20 readings for prediction
                    if len(tension_history[hook_id]) > 20:
                        tension_history[hook_id] = tension_history[hook_id][-20:]
                    
                    # Generate alerts based on tension levels
                    alert_level = get_tension_alert_level(tension)
                    if alert_level != 'safe':
                        prediction = predict_tension_trend(hook_id)
                        alerts.append({
                            'id': hook_id,
                            'berth': berth['name'],
                            'bollard': bollard['name'],
                            'hook': hook['name'],
                            'current_tension': tension,
                            'level': alert_level,
                            'prediction': prediction,
                            'timestamp': datetime.now().isoformat(),
                            'faulted': hook.get('faulted', False),
                            'attached_line': hook.get('attachedLine')
                        })
    
    return sorted(alerts, key=lambda x: get_alert_priority(x['level']), reverse=True)

def get_tension_alert_level(tension):
    """Determine alert level based on tension value"""
    if tension >= alert_thresholds['critical']:
        return 'critical'
    elif tension >= alert_thresholds['high']:
        return 'high'
    elif tension >= alert_thresholds['medium']:
        return 'medium'
    elif tension >= alert_thresholds['low']:
        return 'low'
    else:
        return 'safe'

def get_alert_priority(level):
    """Get numeric priority for alert sorting"""
    priorities = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'safe': 0}
    return priorities.get(level, 0)

def predict_tension_trend(hook_id):
    """Simple linear prediction of tension trend"""
    if hook_id not in tension_history or len(tension_history[hook_id]) < 3:
        return {'trend': 'stable', 'prediction': None}
    
    history = tension_history[hook_id][-10:]  # Use last 10 readings
    tensions = [reading['tension'] for reading in history]
    
    # Calculate simple linear trend
    n = len(tensions)
    x_sum = sum(range(n))
    y_sum = sum(tensions)
    xy_sum = sum(i * tensions[i] for i in range(n))
    x2_sum = sum(i * i for i in range(n))
    
    if n * x2_sum - x_sum * x_sum == 0:
        return {'trend': 'stable', 'prediction': None}
    
    slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
    
    # Predict tension in next 5 minutes (assuming 2-second intervals)
    future_tension = tensions[-1] + slope * 150  # 150 data points = ~5 minutes
    
    if abs(slope) < 0.1:
        trend = 'stable'
    elif slope > 0:
        trend = 'increasing'
    else:
        trend = 'decreasing'
    
    return {
        'trend': trend,
        'slope': round(slope, 3),
        'current': tensions[-1],
        'predicted_5min': round(future_tension, 1),
        'time_to_critical': calculate_time_to_critical(tensions[-1], slope) if slope > 0 else None
    }

def calculate_time_to_critical(current_tension, slope):
    """Calculate estimated time until tension reaches critical level"""
    if slope <= 0:
        return None
    
    time_to_critical = (alert_thresholds['critical'] - current_tension) / slope
    if time_to_critical <= 0:
        return None
    
    # Convert to minutes (assuming 2-second intervals)
    minutes = (time_to_critical * 2) / 60
    return round(minutes, 1) if minutes > 0 else None

def validate_hook_data_accuracy(berth_data):
    """Cross-validate hook tensions for accuracy"""
    hooks = []
    for bollard in berth_data.get('bollards', []):
        hooks.extend(bollard.get('hooks', []))
    
    # Check for anomalies
    tensions = [h.get('tension') for h in hooks if h.get('tension') is not None]
    if not tensions:
        return {'status': 'no_data', 'confidence': 0.0}
    
    avg_tension = sum(tensions) / len(tensions)
    std_dev = statistics.stdev(tensions) if len(tensions) > 1 else 0
    
    # Flag outliers
    outliers = []
    for hook in hooks:
        if hook.get('tension') and abs(hook['tension'] - avg_tension) > 2 * std_dev:
            outliers.append({
                'hook': hook['name'],
                'tension': hook['tension'],
                'expected_range': f"{avg_tension - std_dev:.1f}-{avg_tension + std_dev:.1f}"
            })
    
    return {
        'status': 'validated',
        'confidence': max(0.3, 1.0 - (len(outliers) / len(hooks))) if hooks else 0.0,
        'outliers': outliers,
        'average_tension': avg_tension,
        'standard_deviation': std_dev
    }

def categorize_hooks_by_function(berth_data):
    """Categorize hooks by their mooring function"""
    categories = {
        'bow_lines': [],      # Forward lines
        'stern_lines': [],    # Aft lines  
        'breast_lines': [],   # Side-to-side lines
        'spring_lines': [],   # Angled lines
        'unknown': []         # Unclassified
    }
    
    for bollard in berth_data.get('bollards', []):
        for hook in bollard.get('hooks', []):
            line_type = hook.get('attachedLine', '').upper()
            hook_with_location = {**hook, 'bollard': bollard['name']}
            
            if any(keyword in line_type for keyword in ['BOW', 'FORWARD', 'HEAD']):
                categories['bow_lines'].append(hook_with_location)
            elif any(keyword in line_type for keyword in ['STERN', 'AFT', 'TAIL']):
                categories['stern_lines'].append(hook_with_location)
            elif 'BREAST' in line_type:
                categories['breast_lines'].append(hook_with_location)
            elif 'SPRING' in line_type:
                categories['spring_lines'].append(hook_with_location)
            else:
                categories['unknown'].append(hook_with_location)
    
    return categories

def predict_load_distribution(hook_categories, environmental_factors=None):
    """Predict how environmental factors affect different hook categories"""
    predictions = {}
    
    if environmental_factors:
        wind_speed = environmental_factors.get('wind_speed', 0)
        wind_direction = environmental_factors.get('wind_direction', 'unknown')
        wave_height = environmental_factors.get('wave_height', 0)
        
        # Example predictions based on environmental factors
        if wind_speed > 20:  # High wind
            predictions['breast_lines'] = {
                'tension_change': '+20%', 
                'priority': 'high',
                'reason': f'High wind speed ({wind_speed} knots) increasing lateral loads'
            }
            predictions['spring_lines'] = {
                'tension_change': '+15%', 
                'priority': 'medium',
                'reason': 'Wind-induced ship movement affecting positioning'
            }
        
        if wave_height > 2:  # Rough seas
            predictions['bow_lines'] = {
                'tension_change': '+25%', 
                'priority': 'high',
                'reason': f'Wave action ({wave_height}m) affecting bow stability'
            }
            predictions['stern_lines'] = {
                'tension_change': '+25%', 
                'priority': 'high',
                'reason': f'Wave action ({wave_height}m) affecting stern stability'
            }
    
    return predictions

def generate_hook_status_summary(latest_data):
    """Generate clear, actionable hook status for crew"""
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
            'hook_categories': categorize_hooks_by_function(berth),
            'validation': validate_hook_data_accuracy(berth)
        }
        
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                summary['total_hooks'] += 1
                hook_status = analyze_hook_status(hook, bollard['name'], berth['name'])
                
                if hook_status['alert_level'] in ['high', 'critical']:
                    summary['problematic_hooks'] += 1
                    if hook_status['alert_level'] == 'critical':
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

def analyze_hook_status(hook, bollard_name, berth_name):
    """Analyze individual hook status with communication context"""
    tension = hook.get('tension', 0)
    faulted = hook.get('faulted', False)
    
    status = {
        'location': f"{berth_name}-{bollard_name}-{hook['name']}",
        'tension': tension,
        'alert_level': get_tension_alert_level(tension) if tension else 'unknown',
        'faulted': faulted,
        'communication_priority': 'low',
        'action_required': None,
        'crew_message': None,
        'confidence_score': hook.get('confidence_score', 1.0),
        'sensor_quality': hook.get('sensor_quality', 'good'),
        'line_type': hook.get('attachedLine', 'unknown')
    }
    
    # Generate specific crew messages
    if faulted:
        status['communication_priority'] = 'high'
        status['action_required'] = 'sensor_check'
        status['crew_message'] = f"Sensor fault at {status['location']} - verify manually"
    elif tension and tension >= 95:
        status['communication_priority'] = 'critical'
        status['action_required'] = 'immediate_adjustment'
        status['crew_message'] = f"CRITICAL tension at {status['location']} - release immediately"
    elif tension and tension >= 85:
        status['communication_priority'] = 'high'
        status['action_required'] = 'monitor_adjust'
        status['crew_message'] = f"High tension at {status['location']} - prepare for adjustment"
    elif status['confidence_score'] < 0.7:
        status['communication_priority'] = 'medium'
        status['action_required'] = 'verify_reading'
        status['crew_message'] = f"Low confidence reading at {status['location']} - verify sensor"
    
    return status

def find_hook_by_id(hook_id, data):
    """Find hook by ID in the data structure"""
    if not data or 'berths' not in data:
        return None
    
    for berth in data['berths']:
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

def generate_hook_communication_notes(hook_info):
    """Generate communication notes for specific hook"""
    hook = hook_info['hook']
    tension = hook.get('tension', 0)
    
    notes = []
    
    # Trend analysis
    hook_id = f"{hook_info['berth']}-{hook_info['bollard']}-{hook['name']}"
    prediction = predict_tension_trend(hook_id)
    
    if prediction['trend'] == 'increasing':
        notes.append(f"⬆️ Tension increasing - projected {prediction.get('predicted_5min', 'unknown')}% in 5 minutes")
        if prediction.get('time_to_critical'):
            notes.append(f"⏰ Time to critical: {prediction['time_to_critical']} minutes")
    elif prediction['trend'] == 'decreasing':
        notes.append(f"⬇️ Tension decreasing - continue monitoring")
    else:
        notes.append(f"➡️ Tension stable at {tension}%")
    
    # Line type considerations
    line_type = hook.get('attachedLine', '').upper()
    if 'BREAST' in line_type:
        notes.append("ℹ️ Breast line - critical for lateral stability")
    elif 'SPRING' in line_type:
        notes.append("ℹ️ Spring line - prevents fore/aft movement")
    elif any(keyword in line_type for keyword in ['BOW', 'FORWARD']):
        notes.append("ℹ️ Bow line - controls forward positioning")
    elif any(keyword in line_type for keyword in ['STERN', 'AFT']):
        notes.append("ℹ️ Stern line - controls aft positioning")
    
    # Sensor quality notes
    sensor_quality = hook.get('sensor_quality', 'good')
    if sensor_quality != 'excellent':
        notes.append(f"🔧 Sensor quality: {sensor_quality} - consider recalibration")
    
    # Environmental factors
    env_factors = hook.get('environmental_factors', {})
    if env_factors:
        notes.append("🌊 Environmental factors affecting tension:")
        for factor, value in env_factors.items():
            notes.append(f"  • {factor}: {value}")
    else:
        notes.append("🌊 Check current weather conditions affecting tension")
    
    return notes

def get_hook_recommendations(hook_info):
    """Get specific recommendations for a hook"""
    hook = hook_info['hook']
    tension = hook.get('tension', 0)
    recommendations = []
    
    # Tension-based recommendations
    if tension >= 95:
        recommendations.append({
            'priority': 'CRITICAL',
            'action': 'Release tension immediately',
            'reason': 'Approaching breaking point'
        })
    elif tension >= 85:
        recommendations.append({
            'priority': 'HIGH',
            'action': 'Gradually reduce tension',
            'reason': 'High stress on equipment'
        })
    elif tension < 20:
        recommendations.append({
            'priority': 'MEDIUM',
            'action': 'Consider increasing tension',
            'reason': 'May not be providing adequate hold'
        })
    
    # Sensor-based recommendations
    if hook.get('faulted'):
        recommendations.append({
            'priority': 'HIGH',
            'action': 'Replace faulty sensor',
            'reason': 'Unable to monitor tension accurately'
        })
    
    if hook.get('sensor_quality', 'good') == 'poor':
        recommendations.append({
            'priority': 'MEDIUM',
            'action': 'Schedule sensor maintenance',
            'reason': 'Poor sensor quality affecting readings'
        })
    
    # Maintenance recommendations
    last_maintenance = hook.get('last_maintenance')
    if last_maintenance:
        days_since_maintenance = (datetime.now() - last_maintenance).days
        if days_since_maintenance > 90:
            recommendations.append({
                'priority': 'LOW',
                'action': 'Schedule routine maintenance',
                'reason': f'{days_since_maintenance} days since last maintenance'
            })
    
    return recommendations

@app.post("/")
async def receive_mooring_data(data: PortData):
    """Receive mooring data from the generator"""
    global latest_data, data_history
    
    # Store the data
    latest_data = data.model_dump()
    data_history.append({
        "timestamp": datetime.now().isoformat(),
        "data": latest_data
    })
    
    # Keep only last 100 entries to prevent memory issues
    if len(data_history) > 100:
        data_history = data_history[-100:]
    
    print(f"Received data at {datetime.now()}: Port {data.name} with {len(data.berths)} berths")
    
    return {"status": "received", "timestamp": datetime.now().isoformat()}

@app.get("/api/latest")
async def get_latest_data():
    """API endpoint to get the latest data (for AJAX updates)"""
    return {
        "data": latest_data,
        "count": len(data_history),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/alerts")
async def get_current_alerts():
    """API endpoint to get current tension alerts"""
    alerts = generate_tension_alerts()
    return {"alerts": alerts, "timestamp": datetime.now().isoformat()}

@app.get("/api/tension-history/{hook_id}")
async def get_tension_history_for_hook(hook_id: str):
    """Get tension history for a specific hook"""
    history = tension_history.get(hook_id, [])
    return {"hook_id": hook_id, "history": history[-50:]}  # Last 50 readings

@app.get("/api/crew-briefing")
async def get_crew_briefing():
    """Get formatted briefing for crew shift change"""
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

@app.get("/api/hook-communication/{hook_id}")
async def get_hook_communication_info(hook_id: str):
    """Get detailed communication info for specific hook"""
    hook_info = find_hook_by_id(hook_id, latest_data)
    if not hook_info:
        return {"error": "Hook not found"}
    
    return {
        'hook_id': hook_id,
        'current_status': analyze_hook_status(hook_info['hook'], hook_info['bollard'], hook_info['berth']),
        'recent_history': tension_history.get(hook_id, [])[-10:],
        'communication_notes': generate_hook_communication_notes(hook_info),
        'recommended_actions': get_hook_recommendations(hook_info),
        'ship_info': hook_info.get('ship', 'Unknown'),
        'prediction': predict_tension_trend(hook_id) if hook_id in tension_history else None
    }

@app.get("/api/hook-categories/{berth_name}")
async def get_hook_categories_for_berth(berth_name: str):
    """Get categorized hooks for a specific berth"""
    if not latest_data or 'berths' not in latest_data:
        return {"error": "No data available"}
    
    berth_data = None
    for berth in latest_data['berths']:
        if berth['name'] == berth_name:
            berth_data = berth
            break
    
    if not berth_data:
        return {"error": f"Berth {berth_name} not found"}
    
    categories = categorize_hooks_by_function(berth_data)
    validation = validate_hook_data_accuracy(berth_data)
    
    return {
        'berth_name': berth_name,
        'ship': berth_data['ship']['name'],
        'categories': categories,
        'validation': validation,
        'environmental_predictions': predict_load_distribution(categories),
        'timestamp': datetime.now().isoformat()
    }

@app.post("/api/update-hook-environmental")
async def update_hook_environmental_data(hook_id: str, environmental_data: dict):
    """Update environmental factors for a hook (in real deployment, this would update the database)"""
    # In a real system, this would update the hook's environmental_factors in the database
    # For now, we'll simulate the update
    hook_info = find_hook_by_id(hook_id, latest_data)
    if not hook_info:
        return {"error": "Hook not found"}
    
    # Simulate updating environmental factors
    hook_info['hook']['environmental_factors'] = environmental_data
    
    return {
        'status': 'updated',
        'hook_id': hook_id,
        'environmental_factors': environmental_data,
        'timestamp': datetime.now().isoformat()
    }

@app.get("/api/system-health")
async def get_system_health():
    """Get overall system health and sensor status"""
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

if __name__ == "__main__":
    print("Starting Mooring Data Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:8000")
    print("Generator should POST to: http://127.0.0.1:8000/")
    uvicorn.run(app, host="127.0.0.1", port=8000)
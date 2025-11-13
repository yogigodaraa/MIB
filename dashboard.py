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
import asyncio
import logging
from ship_movement_analyzer import ShipMovementAnalyzer
from enhanced_tension_monitor import EnhancedTensionMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mooring Data Dashboard")
templates = Jinja2Templates(directory="templates")

# Initialize enhanced monitoring systems
enhanced_tension_monitor = EnhancedTensionMonitor()
ship_movement_analyzer = ShipMovementAnalyzer()

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

# Initialize 3D movement analyzer
movement_analyzer = ShipMovementAnalyzer()

# Communication & Alert Management
crew_responses = {}  # Track crew acknowledgments and responses
active_alerts = {}   # Track active alerts and their status
communication_log = []  # Log all communications
crew_status = {}     # Track crew member status and assignments

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

# Communication Models
class CrewMember(BaseModel):
    id: str
    name: str
    role: str  # "deck_officer", "bosun", "engineer", "captain"
    phone: Optional[str] = None
    radio_channel: Optional[str] = None
    location: Optional[str] = None
    status: str = "available"  # "available", "responding", "busy", "off_duty"

class AlertResponse(BaseModel):
    alert_id: str
    crew_member_id: str
    response_type: str  # "acknowledged", "responding", "resolved", "escalated"
    message: Optional[str] = None
    timestamp: datetime
    location: Optional[str] = None

class CommunicationMessage(BaseModel):
    id: str
    message_type: str  # "sms", "push", "radio", "manual"
    recipient: str
    content: str
    priority: str  # "low", "medium", "high", "critical"
    sent_at: datetime
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    status: str = "pending"  # "pending", "sent", "delivered", "acknowledged", "failed"

class ManualDataEntry(BaseModel):
    hook_id: str
    tension_value: int
    entered_by: str
    reason: str  # "sensor_fault", "calibration", "verification"
    timestamp: datetime
    confidence: float = 0.8  # Lower confidence for manual entries

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "latest_data": latest_data,
        "data_count": len(data_history),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

def convert_to_serializable(obj):
    """Convert datetime objects to strings for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj

def calculate_ship_movements():
    """Calculate ship movement data based on radar distances and hook tensions"""
    movements = {}
    
    if not latest_data or 'berths' not in latest_data:
        return movements
    
    for berth in latest_data['berths']:
        ship_name = berth['ship']['name']
        berth_name = berth['name']
        
        # Calculate movement based on radar data
        radar_data = []
        for radar in berth.get('radars', []):
            if radar.get('shipDistance') is not None:
                radar_data.append({
                    'name': radar['name'],
                    'distance': radar['shipDistance'],
                    'distance_change': radar.get('distanceChange', 0),
                    'status': radar['distanceStatus']
                })
        
        # Calculate average distance and movement
        if radar_data:
            avg_distance = sum(r['distance'] for r in radar_data) / len(radar_data)
            avg_change = sum(r['distance_change'] for r in radar_data) / len(radar_data)
        else:
            avg_distance = None
            avg_change = 0
        
        # Analyze hook tensions to determine movement direction
        hook_tensions = []
        hook_analysis = {
            'bow_tension': 0,
            'stern_tension': 0,
            'port_tension': 0,
            'starboard_tension': 0,
            'total_hooks': 0,
            'faulted_hooks': 0
        }
        
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                if hook.get('tension') is not None:
                    hook_tensions.append(hook['tension'])
                    hook_analysis['total_hooks'] += 1
                    
                    # Analyze by line type
                    line_type = hook.get('attachedLine', '').upper()
                    if any(keyword in line_type for keyword in ['BOW', 'FORWARD', 'HEAD']):
                        hook_analysis['bow_tension'] += hook['tension']
                    elif any(keyword in line_type for keyword in ['STERN', 'AFT', 'TAIL']):
                        hook_analysis['stern_tension'] += hook['tension']
                    elif 'PORT' in line_type or 'LEFT' in line_type:
                        hook_analysis['port_tension'] += hook['tension']
                    elif 'STARBOARD' in line_type or 'RIGHT' in line_type:
                        hook_analysis['starboard_tension'] += hook['tension']
                
                if hook.get('faulted', False):
                    hook_analysis['faulted_hooks'] += 1
        
        # Calculate movement indicators
        movement_indicators = calculate_movement_indicators(avg_distance, avg_change, hook_analysis, hook_tensions)
        
        # Predict movement trend
        movement_prediction = predict_movement_trend(berth_name, avg_distance, avg_change, hook_tensions)
        
        movements[berth_name] = {
            'ship_name': ship_name,
            'berth_name': berth_name,
            'current_distance': avg_distance,
            'distance_change': avg_change,
            'radar_data': radar_data,
            'hook_analysis': hook_analysis,
            'movement_indicators': movement_indicators,
            'movement_prediction': movement_prediction,
            'timestamp': datetime.now().isoformat()
        }
    
    return movements

def calculate_movement_indicators(avg_distance, avg_change, hook_analysis, hook_tensions):
    """Calculate various movement indicators based on sensor data"""
    indicators = {
        'movement_direction': 'stable',
        'movement_intensity': 'low',
        'berth_strain': 'normal',
        'stability_score': 85,
        'risk_level': 'low'
    }
    
    # Movement direction based on distance change
    if avg_change and abs(avg_change) > 0.1:
        if avg_change > 0:
            indicators['movement_direction'] = 'moving_away'
        else:
            indicators['movement_direction'] = 'moving_closer'
    
    # Movement intensity based on magnitude of change
    if avg_change and abs(avg_change) > 1.0:
        indicators['movement_intensity'] = 'high'
    elif avg_change and abs(avg_change) > 0.5:
        indicators['movement_intensity'] = 'medium'
    
    # Berth strain analysis
    if hook_tensions:
        avg_tension = sum(hook_tensions) / len(hook_tensions)
        max_tension = max(hook_tensions)
        
        if max_tension > 90 or avg_tension > 75:
            indicators['berth_strain'] = 'high'
            indicators['risk_level'] = 'high'
        elif max_tension > 70 or avg_tension > 60:
            indicators['berth_strain'] = 'medium'
            indicators['risk_level'] = 'medium'
    
    # Calculate stability score
    stability_factors = []
    
    # Distance stability (closer to berth is better)
    if avg_distance:
        if avg_distance < 10:
            stability_factors.append(95)
        elif avg_distance < 20:
            stability_factors.append(85)
        elif avg_distance < 50:
            stability_factors.append(70)
        else:
            stability_factors.append(50)
    
    # Change stability (less movement is better)
    if avg_change:
        if abs(avg_change) < 0.1:
            stability_factors.append(95)
        elif abs(avg_change) < 0.5:
            stability_factors.append(80)
        elif abs(avg_change) < 1.0:
            stability_factors.append(65)
        else:
            stability_factors.append(40)
    
    # Hook tension balance
    if hook_tensions:
        tension_std = statistics.stdev(hook_tensions) if len(hook_tensions) > 1 else 0
        if tension_std < 10:
            stability_factors.append(90)
        elif tension_std < 20:
            stability_factors.append(75)
        else:
            stability_factors.append(60)
    
    # Faulted sensors impact
    if hook_analysis['total_hooks'] > 0:
        fault_ratio = hook_analysis['faulted_hooks'] / hook_analysis['total_hooks']
        stability_factors.append(max(50, 100 - (fault_ratio * 50)))
    
    # Calculate final stability score
    if stability_factors:
        indicators['stability_score'] = int(sum(stability_factors) / len(stability_factors))
    
    return indicators

def predict_movement_trend(berth_name, current_distance, current_change, hook_tensions):
    """Predict future movement trends"""
    prediction = {
        'trend': 'stable',
        'confidence': 0.7,
        'time_horizon': '5_minutes',
        'predicted_distance': current_distance,
        'recommendations': []
    }
    
    # Store movement history for trend analysis
    movement_key = f"movement_{berth_name}"
    if movement_key not in tension_history:
        tension_history[movement_key] = []
    
    # Add current data point
    tension_history[movement_key].append({
        'timestamp': datetime.now().isoformat(),
        'distance': current_distance,
        'change': current_change,
        'avg_tension': sum(hook_tensions) / len(hook_tensions) if hook_tensions else 0
    })
    
    # Keep only last 10 readings
    if len(tension_history[movement_key]) > 10:
        tension_history[movement_key] = tension_history[movement_key][-10:]
    
    # Analyze trend if we have enough data
    if len(tension_history[movement_key]) >= 3:
        recent_changes = [reading['change'] for reading in tension_history[movement_key][-5:]]
        recent_distances = [reading['distance'] for reading in tension_history[movement_key][-5:]]
        
        # Calculate trends
        avg_recent_change = sum(recent_changes) / len(recent_changes)
        distance_trend = recent_distances[-1] - recent_distances[0] if len(recent_distances) > 1 else 0
        
        # Determine trend
        if abs(avg_recent_change) > 0.2:
            if avg_recent_change > 0:
                prediction['trend'] = 'moving_away'
                prediction['predicted_distance'] = current_distance + (avg_recent_change * 10)  # 5min projection
            else:
                prediction['trend'] = 'moving_closer'
                prediction['predicted_distance'] = current_distance + (avg_recent_change * 10)
        
        # Calculate confidence based on consistency
        change_std = statistics.stdev(recent_changes) if len(recent_changes) > 1 else 0
        prediction['confidence'] = max(0.3, 0.9 - (change_std / 10))
    
    # Generate recommendations
    if current_distance and current_distance > 50:
        prediction['recommendations'].append("⚠️ Ship distance increasing - monitor mooring lines")
    
    if current_change and abs(current_change) > 1.0:
        prediction['recommendations'].append("🔴 Significant movement detected - check environmental conditions")
    
    if hook_tensions and max(hook_tensions) > 85:
        prediction['recommendations'].append("🚨 High hook tension detected - consider line adjustment")
    
    if prediction['trend'] == 'moving_away':
        prediction['recommendations'].append("📍 Ship drifting away from berth - verify anchor/mooring security")
    
    return prediction

@app.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Real-time tension monitoring page"""
    alerts = generate_tension_alerts()
    
    # Convert latest_data to JSON-serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "latest_data": serializable_data,
        "alerts": alerts,
        "tension_history": tension_history,
        "thresholds": alert_thresholds,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

@app.get("/ship-3d", response_class=HTMLResponse)
async def ship_3d_page(request: Request):
    """3D ship movement visualization page"""
    movements_3d = calculate_3d_movements()
    
    # Convert latest_data to JSON-serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    return templates.TemplateResponse("ship_3d.html", {
        "request": request,
        "latest_data": serializable_data,
        "movements": movements_3d,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

def calculate_3d_movements():
    """Calculate 3D ship movements using the analyzer"""
    movements = {}
    
    if not latest_data or 'berths' not in latest_data:
        return movements
    
    for berth in latest_data['berths']:
        berth_name = berth['name']
        movement_data = movement_analyzer.analyze_3d_movement(berth, berth_name)
        movements[berth_name] = movement_data
    
    return movements
async def ship_movements_page(request: Request):
    """Ship movement visualization page"""
    movements = calculate_ship_movements()
    
    # Convert latest_data to JSON-serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    return templates.TemplateResponse("ship_movements.html", {
        "request": request,
        "latest_data": serializable_data,
        "movements": movements,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if latest_data else "No data received yet"
    })

def generate_tension_alerts():
    """Generate enhanced tension alerts with improved accuracy"""
    alerts = []
    if not latest_data or 'berths' not in latest_data:
        return alerts
    
    for berth in latest_data['berths']:
        for bollard in berth.get('bollards', []):
            for hook in bollard.get('hooks', []):
                if hook.get('tension') is not None:
                    raw_tension = hook['tension']
                    hook_id = f"{berth['name']}-{bollard['name']}-{hook['name']}"
                    
                    # Process tension reading through enhanced monitor
                    sensor_metadata = {
                        'sensor_quality': hook.get('sensor_quality', 'good'),
                        'calibration_date': hook.get('calibration_date'),
                        'environmental_factors': hook.get('environmental_factors', {}),
                        'faulted': hook.get('faulted', False)
                    }
                    
                    processed_reading = enhanced_tension_monitor.process_tension_reading(
                        hook_id, raw_tension, sensor_metadata
                    )
                    
                    # Store enhanced data in tension history
                    if hook_id not in tension_history:
                        tension_history[hook_id] = []
                    
                    tension_history[hook_id].append({
                        'timestamp': processed_reading['timestamp'].isoformat(),
                        'raw_tension': processed_reading['raw_value'],
                        'processed_tension': processed_reading['processed_value'],
                        'confidence': processed_reading['confidence_score'],
                        'quality_flags': processed_reading['quality_flags'],
                        'is_outlier': processed_reading['is_outlier']
                    })
                    
                    # Keep only last 50 readings for better analysis
                    if len(tension_history[hook_id]) > 50:
                        tension_history[hook_id] = tension_history[hook_id][-50:]
                    
                    # Use processed tension for alert generation
                    tension_to_use = processed_reading['processed_value']
                    if tension_to_use is None:  # Low confidence reading
                        tension_to_use = raw_tension
                    
                    # Generate alerts based on processed tension levels
                    alert_level = get_enhanced_tension_alert_level(
                        tension_to_use, processed_reading['confidence_score'], 
                        processed_reading['quality_flags']
                    )
                    
                    if alert_level != 'safe':
                        prediction = predict_enhanced_tension_trend(hook_id, processed_reading)
                        
                        alert_data = {
                            'id': hook_id,
                            'berth': berth['name'],
                            'bollard': bollard['name'],
                            'hook': hook['name'],
                            'raw_tension': processed_reading['raw_value'],
                            'processed_tension': tension_to_use,
                            'confidence_score': processed_reading['confidence_score'],
                            'level': alert_level,
                            'prediction': prediction,
                            'timestamp': processed_reading['timestamp'].isoformat(),
                            'faulted': hook.get('faulted', False),
                            'attached_line': hook.get('attachedLine'),
                            'quality_flags': processed_reading['quality_flags'],
                            'accuracy_recommendations': processed_reading['recommendations'],
                            'processing_details': {
                                'is_outlier': processed_reading['is_outlier'],
                                'outlier_score': processed_reading['outlier_score'],
                                'drift_correction': processed_reading['drift_correction'],
                                'environmental_correction': processed_reading['environmental_correction'],
                                'cross_validation_delta': processed_reading['cross_validation_delta']
                            }
                        }
                        alerts.append(alert_data)
                        
                        # Trigger communication cascade for new critical/high alerts
                        if alert_level in ['critical', 'high'] and hook_id not in active_alerts:
                            asyncio.create_task(trigger_alert_cascade(alert_data))
    
    return sorted(alerts, key=lambda x: get_alert_priority(x['level']), reverse=True)

def get_enhanced_tension_alert_level(tension, confidence_score, quality_flags):
    """Enhanced alert level determination with confidence and quality considerations"""
    base_level = get_tension_alert_level(tension)
    
    # Adjust alert level based on confidence and quality
    if confidence_score < 0.5:
        # Low confidence readings get elevated alert level for caution
        if base_level == 'safe':
            return 'low'
        elif base_level == 'low':
            return 'medium'
    
    # Check quality flags for additional concerns
    if 'SENSOR_DEGRADATION' in quality_flags or 'CALIBRATION_OVERDUE' in quality_flags:
        if base_level in ['safe', 'low']:
            return 'medium'  # Elevate due to sensor issues
    
    if 'LOW_CONFIDENCE' in quality_flags and base_level in ['medium', 'high']:
        # For higher tensions with low confidence, maintain alert but flag uncertainty
        pass
    
    return base_level

def predict_enhanced_tension_trend(hook_id, processed_reading):
    """Enhanced tension trend prediction using processed data"""
    if hook_id not in tension_history or len(tension_history[hook_id]) < 3:
        return {'trend': 'stable', 'prediction': None, 'confidence': 0.5}
    
    history = tension_history[hook_id][-15:]  # Use last 15 readings
    
    # Filter out low-confidence readings for trend analysis
    reliable_readings = [r for r in history if r.get('confidence', 0) > 0.6]
    
    if len(reliable_readings) < 3:
        return {'trend': 'insufficient_data', 'prediction': None, 'confidence': 0.3}
    
    # Use processed tensions for trend calculation
    tensions = [r['processed_tension'] for r in reliable_readings if r['processed_tension'] is not None]
    
    if len(tensions) < 3:
        # Fall back to raw tensions if processed unavailable
        tensions = [r['raw_tension'] for r in reliable_readings]
    
    # Enhanced linear trend calculation with outlier filtering
    # Remove outliers before trend calculation
    if len(tensions) > 5:
        mean_tension = statistics.mean(tensions)
        std_tension = statistics.stdev(tensions)
        filtered_tensions = [t for t in tensions if abs(t - mean_tension) <= 2 * std_tension]
        if len(filtered_tensions) >= 3:
            tensions = filtered_tensions
    
    # Calculate trend
    n = len(tensions)
    if n < 2:
        return {'trend': 'stable', 'prediction': None, 'confidence': 0.4}
    
    x_sum = sum(range(n))
    y_sum = sum(tensions)
    xy_sum = sum(i * tensions[i] for i in range(n))
    x2_sum = sum(i * i for i in range(n))
    
    if n * x2_sum - x_sum * x_sum == 0:
        return {'trend': 'stable', 'prediction': None, 'confidence': 0.5}
    
    slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
    intercept = (y_sum - slope * x_sum) / n
    
    # Predict tension in next 5 minutes (assuming readings every 10 seconds)
    future_steps = 30  # 5 minutes / 10 seconds
    future_tension = tensions[-1] + slope * future_steps
    
    # Determine trend direction with enhanced logic
    if abs(slope) < 0.05:  # Very small slope
        trend = 'stable'
    elif slope > 0.2:  # Significant upward trend
        trend = 'rapidly_increasing'
    elif slope > 0.05:
        trend = 'increasing'
    elif slope < -0.2:  # Significant downward trend
        trend = 'rapidly_decreasing'
    elif slope < -0.05:
        trend = 'decreasing'
    else:
        trend = 'stable'
    
    # Calculate confidence based on data quality
    avg_confidence = statistics.mean([r.get('confidence', 0.7) for r in reliable_readings])
    trend_confidence = min(1.0, avg_confidence * (len(reliable_readings) / 10.0))
    
    # Calculate R-squared for trend reliability
    if len(tensions) > 2:
        y_pred = [intercept + slope * i for i in range(len(tensions))]
        ss_res = sum((tensions[i] - y_pred[i])**2 for i in range(len(tensions)))
        ss_tot = sum((t - statistics.mean(tensions))**2 for t in tensions)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        trend_confidence *= max(0.3, r_squared)
    
    prediction_result = {
        'trend': trend,
        'slope': round(slope, 4),
        'current': tensions[-1],
        'predicted_5min': round(future_tension, 1),
        'confidence': round(trend_confidence, 3),
        'r_squared': round(r_squared if 'r_squared' in locals() else 0, 3),
        'data_points_used': len(tensions),
        'time_to_critical': calculate_time_to_critical_enhanced(tensions[-1], slope) if slope > 0 else None,
        'quality_assessment': assess_prediction_quality(reliable_readings, processed_reading)
    }
    
    return prediction_result

def calculate_time_to_critical_enhanced(current_tension, slope):
    """Enhanced calculation of time to critical tension level"""
    if slope <= 0:
        return None
    
    critical_threshold = alert_thresholds['critical']
    time_to_critical = (critical_threshold - current_tension) / slope
    
    if time_to_critical <= 0:
        return None
    
    # Convert to minutes (assuming readings every 10 seconds)
    minutes = (time_to_critical * 10) / 60
    return round(minutes, 1) if minutes > 0 else None

def assess_prediction_quality(recent_readings, current_reading):
    """Assess the quality of tension prediction"""
    quality = {
        'overall_score': 0.7,
        'factors': []
    }
    
    # Check data consistency
    confidences = [r.get('confidence', 0.7) for r in recent_readings]
    avg_confidence = statistics.mean(confidences)
    
    if avg_confidence > 0.8:
        quality['factors'].append('High sensor confidence')
        quality['overall_score'] += 0.1
    elif avg_confidence < 0.5:
        quality['factors'].append('Low sensor confidence')
        quality['overall_score'] -= 0.2
    
    # Check for outliers in recent data
    outlier_count = sum(1 for r in recent_readings if r.get('is_outlier', False))
    outlier_ratio = outlier_count / len(recent_readings)
    
    if outlier_ratio > 0.3:
        quality['factors'].append('High outlier rate')
        quality['overall_score'] -= 0.15
    elif outlier_ratio < 0.1:
        quality['factors'].append('Low outlier rate')
        quality['overall_score'] += 0.05
    
    # Check sensor health flags
    current_flags = current_reading.get('quality_flags', [])
    if 'CALIBRATION_OVERDUE' in current_flags:
        quality['factors'].append('Sensor calibration overdue')
        quality['overall_score'] -= 0.1
    
    if 'SENSOR_DEGRADATION' in current_flags:
        quality['factors'].append('Sensor degradation detected')
        quality['overall_score'] -= 0.15
    
    quality['overall_score'] = max(0.1, min(1.0, quality['overall_score']))
    
    return quality

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

# Communication Engine Functions
async def send_sms_alert(phone_number: str, message: str, priority: str = "medium"):
    """Send SMS alert to crew member (integration point for Twilio/etc)"""
    # In production, integrate with Twilio or similar service
    # For demo purposes, we'll simulate the SMS
    
    message_id = f"sms_{datetime.now().timestamp()}"
    
    # Log the communication
    comm_message = {
        "id": message_id,
        "message_type": "sms",
        "recipient": phone_number,
        "content": message,
        "priority": priority,
        "sent_at": datetime.now().isoformat(),
        "status": "sent"  # In real implementation: "pending" → "sent" → "delivered"
    }
    
    communication_log.append(comm_message)
    
    # Simulate SMS delivery delay
    await asyncio.sleep(0.1)
    
    logger.info(f"SMS sent to {phone_number}: {message}")
    return message_id

async def send_push_notification(crew_id: str, title: str, message: str, priority: str = "medium"):
    """Send push notification to crew mobile app"""
    # Integration point for Firebase/APNs/etc
    
    message_id = f"push_{datetime.now().timestamp()}"
    
    comm_message = {
        "id": message_id,
        "message_type": "push",
        "recipient": crew_id,
        "content": f"{title}: {message}",
        "priority": priority,
        "sent_at": datetime.now().isoformat(),
        "status": "sent"
    }
    
    communication_log.append(comm_message)
    
    logger.info(f"Push notification sent to {crew_id}: {title}")
    return message_id

async def broadcast_radio_alert(message: str, channel: str = "bridge"):
    """Broadcast critical alert over radio system"""
    # Integration point for radio transmission hardware
    
    message_id = f"radio_{datetime.now().timestamp()}"
    
    comm_message = {
        "id": message_id,
        "message_type": "radio",
        "recipient": f"channel_{channel}",
        "content": message,
        "priority": "critical",
        "sent_at": datetime.now().isoformat(),
        "status": "broadcasted"
    }
    
    communication_log.append(comm_message)
    
    logger.info(f"Radio broadcast on {channel}: {message}")
    return message_id

def process_crew_response(alert_id: str, crew_id: str, response_type: str, message: str = None):
    """Process crew response to an alert"""
    
    response = {
        "alert_id": alert_id,
        "crew_member_id": crew_id,
        "response_type": response_type,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "location": crew_status.get(crew_id, {}).get("location", "unknown")
    }
    
    # Store response
    if alert_id not in crew_responses:
        crew_responses[alert_id] = []
    crew_responses[alert_id].append(response)
    
    # Update crew status
    if crew_id in crew_status:
        if response_type == "acknowledged":
            crew_status[crew_id]["status"] = "responding"
        elif response_type == "resolved":
            crew_status[crew_id]["status"] = "available"
    
    # Update alert status
    if alert_id in active_alerts:
        active_alerts[alert_id]["last_response"] = response
        if response_type == "resolved":
            active_alerts[alert_id]["status"] = "resolved"
            active_alerts[alert_id]["resolved_at"] = datetime.now().isoformat()
    
    logger.info(f"Crew response recorded: {crew_id} {response_type} alert {alert_id}")
    
    return response

async def trigger_alert_cascade(alert_data: dict):
    """Trigger appropriate communication channels based on alert level"""
    
    alert_level = alert_data.get('level', 'low')
    hook_id = alert_data.get('id', 'unknown')
    tension = alert_data.get('current_tension', 0)
    prediction = alert_data.get('prediction', {})
    
    # Generate alert ID
    alert_id = f"alert_{datetime.now().timestamp()}"
    
    # Store active alert
    active_alerts[alert_id] = {
        "id": alert_id,
        "hook_id": hook_id,
        "level": alert_level,
        "tension": tension,
        "prediction": prediction,
        "created_at": datetime.now().isoformat(),
        "status": "active",
        "communications_sent": []
    }
    
    # Prepare alert messages
    location = alert_data.get('berth', 'Unknown') + " - " + alert_data.get('hook', 'Unknown Hook')
    
    if alert_level == "critical":
        # CRITICAL: Radio + SMS + Push
        radio_msg = f"EMERGENCY: Critical tension at {location}. {tension}% load. Immediate action required."
        sms_msg = f"🚨 CRITICAL: {location} at {tension}% tension. {prediction.get('time_to_critical', 'Unknown')} min to failure. ACT NOW!"
        push_title = "CRITICAL TENSION ALERT"
        push_msg = f"{location}: {tension}% load - Immediate action required"
        
        # Send all communication types
        radio_id = await broadcast_radio_alert(radio_msg, "emergency")
        
        # Send to all available crew
        for crew_id, crew_info in crew_status.items():
            if crew_info.get("status") != "off_duty":
                sms_id = await send_sms_alert(crew_info.get("phone", ""), sms_msg, "critical")
                push_id = await send_push_notification(crew_id, push_title, push_msg, "critical")
                
                active_alerts[alert_id]["communications_sent"].extend([radio_id, sms_id, push_id])
    
    elif alert_level == "high":
        # HIGH: SMS + Push to relevant crew
        sms_msg = f"⚠️ HIGH tension alert: {location} at {tension}% load. Monitor and prepare for adjustment."
        push_title = "High Tension Alert"
        push_msg = f"{location}: {tension}% - Monitor closely"
        
        # Send to deck officers and bosun
        for crew_id, crew_info in crew_status.items():
            if crew_info.get("role") in ["deck_officer", "bosun"] and crew_info.get("status") != "off_duty":
                sms_id = await send_sms_alert(crew_info.get("phone", ""), sms_msg, "high")
                push_id = await send_push_notification(crew_id, push_title, push_msg, "high")
                
                active_alerts[alert_id]["communications_sent"].extend([sms_id, push_id])
    
    elif alert_level == "medium":
        # MEDIUM: Push notifications only
        push_title = "Tension Warning"
        push_msg = f"{location}: {tension}% tension - Attention required"
        
        # Send to relevant crew
        for crew_id, crew_info in crew_status.items():
            if crew_info.get("status") == "available":
                push_id = await send_push_notification(crew_id, push_title, push_msg, "medium")
                active_alerts[alert_id]["communications_sent"].append(push_id)
    
    return alert_id

def get_crew_status_summary():
    """Get summary of all crew member statuses"""
    summary = {
        "total_crew": len(crew_status),
        "available": 0,
        "responding": 0,
        "busy": 0,
        "off_duty": 0,
        "crew_details": []
    }
    
    for crew_id, crew_info in crew_status.items():
        status = crew_info.get("status", "unknown")
        summary[status] = summary.get(status, 0) + 1
        
        # Get latest activity
        latest_response = None
        for alert_responses in crew_responses.values():
            for response in alert_responses:
                if response["crew_member_id"] == crew_id:
                    if not latest_response or response["timestamp"] > latest_response["timestamp"]:
                        latest_response = response
        
        crew_detail = {
            "id": crew_id,
            "name": crew_info.get("name", "Unknown"),
            "role": crew_info.get("role", "Unknown"),
            "status": status,
            "location": crew_info.get("location", "Unknown"),
            "latest_activity": latest_response["timestamp"] if latest_response else "No recent activity"
        }
        summary["crew_details"].append(crew_detail)
    
    return summary

# Initialize sample crew data
crew_status = {
    "crew_001": {
        "name": "Chief Officer Johnson",
        "role": "deck_officer", 
        "phone": "+61400123456",
        "radio_channel": "bridge",
        "location": "Bridge",
        "status": "available"
    },
    "crew_002": {
        "name": "Bosun Smith",
        "role": "bosun",
        "phone": "+61400654321", 
        "radio_channel": "deck",
        "location": "Foredeck",
        "status": "available"
    },
    "crew_003": {
        "name": "AB Williams",
        "role": "able_seaman",
        "phone": "+61400789012",
        "radio_channel": "deck", 
        "location": "Stern",
        "status": "available"
    }
}

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

@app.get("/api/ship-movements")
async def get_ship_movements():
    """API endpoint to get current ship movements data"""
    movements = calculate_ship_movements()
    return {"movements": movements, "timestamp": datetime.now().isoformat()}

@app.get("/api/enhanced-tension/{hook_id}")
async def get_enhanced_tension_data(hook_id: str):
    """Get detailed enhanced tension data for a specific hook"""
    if hook_id not in tension_history or not tension_history[hook_id]:
        return {"error": "No data available for this hook"}
    
    recent_data = tension_history[hook_id][-20:]  # Last 20 readings
    
    # Get accuracy summary for this hook
    accuracy_summary = enhanced_tension_monitor.get_accuracy_summary()
    
    return {
        "hook_id": hook_id,
        "recent_readings": recent_data,
        "accuracy_summary": accuracy_summary,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system-accuracy-status")
async def get_system_accuracy_status():
    """Get overall system accuracy and sensor health status"""
    accuracy_summary = enhanced_tension_monitor.get_accuracy_summary()
    
    # Add additional system health metrics
    total_hooks = 0
    active_hooks = 0
    outlier_hooks = 0
    low_confidence_hooks = 0
    
    for hook_id, history in tension_history.items():
        if history:
            total_hooks += 1
            latest = history[-1]
            
            if latest.get('confidence', 0) > 0.6:
                active_hooks += 1
            
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

def generate_system_accuracy_recommendations(accuracy_summary):
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

@app.get("/api/ship-3d-movements")
async def get_ship_3d_movements():
    """API endpoint to get current 3D ship movements data"""
    movements_3d = calculate_3d_movements()
    return {"movements": movements_3d, "timestamp": datetime.now().isoformat()}

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

@app.get("/api/crew-status")
async def get_crew_status():
    """Get current crew status and assignments"""
    return get_crew_status_summary()

@app.post("/api/crew-response")
async def record_crew_response(alert_id: str, crew_id: str, response_type: str, message: str = None):
    """Record crew response to an alert"""
    response = process_crew_response(alert_id, crew_id, response_type, message)
    return {"status": "recorded", "response": response}

@app.get("/api/communication-log")
async def get_communication_log(limit: int = 50):
    """Get recent communication log"""
    return {
        "communications": communication_log[-limit:],
        "total_count": len(communication_log),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/active-alerts")
async def get_active_alerts():
    """Get all active alerts with their status"""
    active = {k: v for k, v in active_alerts.items() if v.get("status") == "active"}
    return {
        "active_alerts": active,
        "total_active": len(active),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/manual-data-entry")
async def submit_manual_data(hook_id: str, tension_value: int, crew_id: str, reason: str):
    """Submit manual tension data when sensors fail"""
    
    # Validate input
    if not (0 <= tension_value <= 100):
        return {"error": "Tension value must be between 0 and 100"}
    
    if crew_id not in crew_status:
        return {"error": "Unknown crew member"}
    
    # Create manual entry record
    entry = {
        "hook_id": hook_id,
        "tension_value": tension_value,
        "entered_by": crew_id,
        "crew_name": crew_status[crew_id].get("name", "Unknown"),
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "confidence": 0.8,  # Lower confidence for manual entries
        "type": "manual_entry"
    }
    
    # Store in tension history with special marker
    if hook_id not in tension_history:
        tension_history[hook_id] = []
    
    tension_history[hook_id].append({
        'timestamp': entry["timestamp"],
        'tension': tension_value,
        'manual': True,
        'entered_by': crew_id,
        'reason': reason
    })
    
    # Log the manual entry
    communication_log.append({
        "id": f"manual_{datetime.now().timestamp()}",
        "message_type": "manual",
        "recipient": "system",
        "content": f"Manual data entry: {hook_id} = {tension_value}% (Reason: {reason})",
        "priority": "medium",
        "sent_at": datetime.now().isoformat(),
        "status": "recorded"
    })
    
    logger.info(f"Manual data entry: {hook_id} = {tension_value}% by {crew_id}")
    
    return {"status": "recorded", "entry": entry}

@app.post("/api/broadcast-alert")
async def broadcast_custom_alert(message: str, priority: str = "medium", channels: List[str] = ["sms", "push"]):
    """Broadcast custom alert message to crew"""
    
    message_ids = []
    
    if "radio" in channels and priority == "critical":
        radio_id = await broadcast_radio_alert(message, "all")
        message_ids.append(radio_id)
    
    if "sms" in channels:
        for crew_id, crew_info in crew_status.items():
            if crew_info.get("status") != "off_duty" and crew_info.get("phone"):
                sms_id = await send_sms_alert(crew_info["phone"], f"📢 BROADCAST: {message}", priority)
                message_ids.append(sms_id)
    
    if "push" in channels:
        for crew_id, crew_info in crew_status.items():
            if crew_info.get("status") != "off_duty":
                push_id = await send_push_notification(crew_id, "Broadcast Alert", message, priority)
                message_ids.append(push_id)
    
    return {
        "status": "broadcasted",
        "message_ids": message_ids,
        "channels_used": channels,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("Starting Mooring Data Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:8000")
    print("Generator should POST to: http://127.0.0.1:8000/")
    uvicorn.run(app, host="127.0.0.1", port=8000)
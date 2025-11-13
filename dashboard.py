#!/usr/bin/env python3
"""
Mooring Data Dashboard
A FastAPI web dashboard to visualize incoming mooring data in real-time.
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Union
import json
from datetime import datetime, timedelta
import uvicorn
import random
import math

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

if __name__ == "__main__":
    print("Starting Mooring Data Dashboard...")
    print("Dashboard will be available at: http://127.0.0.1:8000")
    print("Generator should POST to: http://127.0.0.1:8000/")
    uvicorn.run(app, host="127.0.0.1", port=8000)
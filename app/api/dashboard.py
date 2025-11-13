"""
Main Dashboard Routes
Routes for serving HTML pages and main dashboard functionality.
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..services import DataManagementService, TensionMonitoringService, MovementAnalysisService
from ..utils.helpers import convert_to_serializable

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Service instances (these will be injected in main.py)
data_service: DataManagementService = None
tension_service: TensionMonitoringService = None
movement_service: MovementAnalysisService = None


def init_services(data_svc, tension_svc, movement_svc):
    """Initialize service dependencies"""
    global data_service, tension_service, movement_service
    data_service = data_svc
    tension_service = tension_svc
    movement_service = movement_svc


def get_tension_class(tension):
    """Helper function to get CSS class based on tension level"""
    alert_thresholds = {
        'critical': 95,
        'high': 85,
        'medium': 70,
        'low': 30
    }
    
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


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    latest_data = data_service.get_latest_data()
    data_history = data_service.get_data_history()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "latest_data": latest_data,
        "data_count": len(data_history),
        "last_updated": latest_data.get('timestamp', 'No data received yet') if latest_data else "No data received yet"
    })


@router.get("/monitoring", response_class=HTMLResponse)
async def monitoring_page(request: Request):
    """Real-time tension monitoring page"""
    latest_data = data_service.get_latest_data()
    tension_history = data_service.get_all_tension_history()
    
    # Convert to serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    # Generate alerts using tension service
    alerts = []
    if latest_data:
        # This would be integrated with the tension monitoring service
        # For now, we'll use a simplified version
        pass
    
    return templates.TemplateResponse("monitoring.html", {
        "request": request,
        "latest_data": serializable_data,
        "alerts": alerts,
        "tension_history": tension_history,
        "thresholds": tension_service.config['alert_thresholds'] if tension_service else {},
        "last_updated": latest_data.get('timestamp', 'No data received yet') if latest_data else "No data received yet"
    })


@router.get("/ship-3d", response_class=HTMLResponse)
async def ship_3d_page(request: Request):
    """3D ship movement visualization page"""
    latest_data = data_service.get_latest_data()
    
    # Calculate 3D movements
    movements_3d = {}
    if latest_data and movement_service:
        for berth in latest_data.get('berths', []):
            if not berth or 'name' not in berth:
                continue
            berth_name = berth['name']
            try:
                movement_data = movement_service.analyze_3d_movement(berth, berth_name)
                movements_3d[berth_name] = movement_data.dict()
            except Exception as e:
                print(f"Error analyzing 3D movement for berth {berth_name}: {e}")
                movements_3d[berth_name] = {}
    
    # Convert to serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    return templates.TemplateResponse("ship_3d.html", {
        "request": request,
        "latest_data": serializable_data,
        "movements": {},  # Empty movements dict to avoid template errors
        "last_updated": latest_data.get('timestamp', 'No data received yet') if latest_data else "No data received yet"
    })


@router.get("/ship-movements", response_class=HTMLResponse)
async def ship_movements_page(request: Request):
    """Ship movement visualization page"""
    latest_data = data_service.get_latest_data()
    
    # Calculate ship movements
    movements = {}
    if latest_data and movement_service:
        for berth in latest_data.get('berths', []):
            if not berth or 'name' not in berth:
                continue
            berth_name = berth['name']
            try:
                movement_data = movement_service.analyze_3d_movement(berth, berth_name)
                movements[berth_name] = movement_data.dict()
            except Exception as e:
                print(f"Error analyzing movement for berth {berth_name}: {e}")
                movements[berth_name] = {}
    
    # Convert to serializable format
    serializable_data = None
    if latest_data:
        serializable_data = convert_to_serializable(latest_data)
    
    return templates.TemplateResponse("ship_movements.html", {
        "request": request,
        "latest_data": serializable_data,
        "movements": {},  # Empty movements dict to avoid template errors
        "last_updated": latest_data.get('timestamp', 'No data received yet') if latest_data else "No data received yet"
    })
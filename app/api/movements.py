"""
Movement Analysis API Routes
API endpoints for ship movement analysis and 3D visualization.
"""

from fastapi import APIRouter
from datetime import datetime
from typing import Dict

from ..services import MovementAnalysisService, DataManagementService

router = APIRouter(prefix="/api")

# Service instances (will be injected in main.py)
movement_service: MovementAnalysisService = None
data_service: DataManagementService = None


def init_services(movement_svc, data_svc):
    """Initialize service dependencies"""
    global movement_service, data_service
    movement_service = movement_svc
    data_service = data_svc


@router.get("/ship-movements")
async def get_ship_movements():
    """API endpoint to get current ship movements data"""
    movements = calculate_ship_movements()
    return {"movements": movements, "timestamp": datetime.now().isoformat()}


@router.get("/ship-3d-movements")
async def get_ship_3d_movements():
    """API endpoint to get current 3D ship movements data"""
    movements_3d = calculate_3d_movements()
    return {"movements": movements_3d, "timestamp": datetime.now().isoformat()}


def calculate_ship_movements() -> Dict:
    """Calculate ship movement data based on radar distances and hook tensions"""
    movements = {}
    latest_data = data_service.get_latest_data()
    
    if not latest_data or 'berths' not in latest_data:
        return movements
    
    for berth in latest_data['berths']:
        berth_name = berth['name']
        
        if movement_service:
            # Use the movement service to analyze 3D movement
            movement_data = movement_service.analyze_3d_movement(berth, berth_name)
            movements[berth_name] = movement_data.dict()
        else:
            # Fallback basic calculation
            ship_name = berth['ship']['name']
            
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
            
            movements[berth_name] = {
                'ship_name': ship_name,
                'berth_name': berth_name,
                'current_distance': avg_distance,
                'distance_change': avg_change,
                'radar_data': radar_data,
                'timestamp': datetime.now().isoformat()
            }
    
    return movements


def calculate_3d_movements() -> Dict:
    """Calculate 3D ship movements using the analyzer"""
    movements = {}
    latest_data = data_service.get_latest_data()
    
    if not latest_data or 'berths' not in latest_data:
        return movements
    
    for berth in latest_data['berths']:
        berth_name = berth['name']
        
        if movement_service:
            movement_data = movement_service.analyze_3d_movement(berth, berth_name)
            movements[berth_name] = movement_data.dict()
    
    return movements


@router.get("/movement-summary")
async def get_movement_summary():
    """Get summary of all ship movements"""
    if movement_service:
        summary = movement_service.get_movement_summary()
        return {
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "error": "Movement service not available",
            "timestamp": datetime.now().isoformat()
        }


@router.get("/berth-movements/{berth_name}")
async def get_berth_movements(berth_name: str):
    """Get movement data for a specific berth"""
    latest_data = data_service.get_latest_data()
    
    if not latest_data or 'berths' not in latest_data:
        return {"error": "No data available"}
    
    # Find the specific berth
    berth_data = None
    for berth in latest_data['berths']:
        if berth['name'] == berth_name:
            berth_data = berth
            break
    
    if not berth_data:
        return {"error": f"Berth {berth_name} not found"}
    
    if movement_service:
        movement_data = movement_service.analyze_3d_movement(berth_data, berth_name)
        return {
            "berth_name": berth_name,
            "movement": movement_data.dict(),
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "berth_name": berth_name,
            "error": "Movement service not available",
            "timestamp": datetime.now().isoformat()
        }
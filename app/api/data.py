"""
Data API Routes
API endpoints for data reception and retrieval.
"""

from fastapi import APIRouter
from datetime import datetime

from ..models import PortData
from ..services import DataManagementService

router = APIRouter()

# Service instance (will be injected in main.py)
data_service: DataManagementService = None


def init_services(data_svc):
    """Initialize service dependencies"""
    global data_service
    data_service = data_svc


@router.post("/")
async def receive_mooring_data(data: PortData):
    """Receive mooring data from the generator"""
    result = data_service.receive_port_data(data)
    
    print(f"Received data at {datetime.now()}: Port {data.name} with {len(data.berths)} berths")
    
    return result


@router.get("/api/latest")
async def get_latest_data():
    """API endpoint to get the latest data (for AJAX updates)"""
    latest_data = data_service.get_latest_data()
    data_history = data_service.get_data_history()
    
    return {
        "data": latest_data,
        "count": len(data_history),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/api/system-stats")
async def get_system_stats():
    """Get system statistics and health information"""
    return data_service.get_system_stats()


@router.get("/api/tension-history/{hook_id}")
async def get_tension_history_for_hook(hook_id: str, limit: int = 50):
    """Get tension history for a specific hook"""
    history = data_service.get_tension_history(hook_id, limit)
    return {"hook_id": hook_id, "history": history}


@router.get("/api/berth/{berth_name}")
async def get_berth_data(berth_name: str):
    """Get data for a specific berth"""
    berth_data = data_service.get_berth_data(berth_name)
    if not berth_data:
        return {"error": f"Berth {berth_name} not found"}
    
    return {"berth": berth_data}


@router.get("/api/hooks/berth/{berth_name}")
async def get_hooks_by_berth(berth_name: str):
    """Get all hooks for a specific berth"""
    hooks = data_service.get_hooks_by_berth(berth_name)
    return {"berth_name": berth_name, "hooks": hooks}
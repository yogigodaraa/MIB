# BHP Mooring Data Dashboard - NEW MODULAR VERSION

A comprehensive, professional monitoring system for ship mooring operations with completely refactored, modular architecture.

## ✨ Complete Application Restructure

The entire application has been transformed from a single monolithic file into a clean, maintainable, and professional modular architecture:

```
bhp-data/
├── app/                          # Main application package
│   ├── api/                      # API route modules
│   │   ├── dashboard.py          # Dashboard HTML routes
│   │   ├── data.py              # Data reception and retrieval
│   │   ├── monitoring.py        # Monitoring and alerts
│   │   ├── movements.py         # Movement analysis
│   │   └── communication.py     # Crew communication
│   ├── core/                    # Core configuration
│   │   ├── config.py            # Application settings
│   │   └── logging_config.py    # Logging configuration
│   ├── models/                  # Data models
│   │   ├── ship.py             # Ship data models
│   │   ├── sensors.py          # Sensor data models
│   │   ├── infrastructure.py   # Port infrastructure models
│   │   ├── communication.py    # Communication models
│   │   └── analysis.py         # Analysis result models
│   ├── services/               # Business logic services
│   │   ├── data_management.py  # Data storage and retrieval
│   │   ├── tension_monitoring.py # Enhanced tension analysis
│   │   ├── movement_analysis.py # 3D movement calculations
│   │   └── communication.py   # Crew communication system
│   └── utils/                  # Utility functions
│       └── helpers.py          # Common helper functions
├── templates/                  # HTML templates (preserved)
├── main.py                    # Clean application entry point
├── requirements.txt           # Updated dependencies
├── dashboard.py              # Original file (can be removed)
└── README_NEW.md            # This documentation
```

## 🚀 Key Improvements

### Professional Architecture
- ✅ **Separation of Concerns** - Each module has a single, clear responsibility
- ✅ **Service Layer Architecture** - Business logic is centralized and reusable
- ✅ **Type-Safe Data Models** - Pydantic models ensure data integrity
- ✅ **Modular API Routes** - Organized by functionality, not size
- ✅ **Dependency Injection** - Services are properly injected and manageable
- ✅ **Configuration Management** - Environment-based settings with validation

### Enhanced Maintainability  
- ✅ **Clear File Organization** - Easy to find and modify specific functionality
- ✅ **Testable Components** - Services can be easily mocked and unit tested
- ✅ **Code Reusability** - Common functions are centralized in utilities
- ✅ **Documentation** - Well-documented code with proper type hints
- ✅ **Error Handling** - Consistent error handling across all modules

## 🛠 Installation & Setup

1. **Navigate to the project directory:**
   ```bash
   cd /Users/yogigodara/Downloads/Projects/bhp-data
   ```

2. **Activate your virtual environment:**
   ```bash
   source .venv/bin/activate
   ```

3. **Install updated dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the new modular application:**
   ```bash
   python main.py
   ```

5. **Access the dashboard:**
   - Main Dashboard: http://127.0.0.1:8000
   - Monitoring Page: http://127.0.0.1:8000/monitoring
   - 3D Visualization: http://127.0.0.1:8000/ship-3d
   - API Documentation: http://127.0.0.1:8000/docs

## 🔧 Configuration Options

Create a `.env` file for custom configuration:

```env
# Server Settings
HOST=127.0.0.1
PORT=8000
DEBUG=false

# Alert Thresholds
ALERT_THRESHOLDS='{"low": 30, "medium": 70, "high": 85, "critical": 95}'

# Communication Settings  
SMS_ENABLED=false
PUSH_NOTIFICATIONS_ENABLED=true
RADIO_ENABLED=false

# Data Management
DATA_RETENTION_HOURS=24
MAX_HISTORY_ENTRIES=100
MAX_TENSION_HISTORY=50

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

## 📡 Enhanced API Structure

### Data Management
- `POST /` - Receive mooring data from generators
- `GET /api/latest` - Get latest received data
- `GET /api/system-stats` - System statistics and health
- `GET /api/berth/{berth_name}` - Specific berth data

### Monitoring & Analytics
- `GET /api/alerts` - Current tension alerts with predictions
- `GET /api/system-health` - Overall system health status
- `GET /api/enhanced-tension/{hook_id}` - Detailed hook analysis
- `GET /api/system-accuracy-status` - Sensor accuracy status

### Movement Analysis
- `GET /api/ship-movements` - Current ship movement data
- `GET /api/ship-3d-movements` - 3D movement visualization data
- `GET /api/movement-summary` - System-wide movement summary
- `GET /api/berth-movements/{berth_name}` - Berth-specific movements

### Communication & Operations
- `GET /api/crew-status` - Crew member status and assignments
- `POST /api/manual-data-entry` - Submit manual sensor readings
- `POST /api/broadcast-alert` - Send custom alerts to crew
- `GET /api/crew-briefing` - Shift change briefing data
- `POST /api/crew-response` - Record crew responses to alerts

## 🏗 Architecture Deep Dive

### Services Layer (Business Logic)

**DataManagementService**
- Handles all data reception, storage, and retrieval
- Manages data history and cleanup policies
- Provides data validation and transformation

**TensionMonitoringService**  
- Advanced tension analysis with accuracy improvements
- Outlier detection and sensor drift compensation
- Predictive analytics for tension trends
- Quality scoring and confidence calculations

**MovementAnalysisService**
- 3D ship movement calculations and predictions
- Pattern recognition for oscillations and drift
- Risk assessment and stability scoring
- Environmental factor integration

**CommunicationService**
- Multi-channel crew communication (SMS, Push, Radio)
- Alert escalation and response tracking
- Crew status management and shift coordination
- Manual data entry processing

### Models Layer (Data Validation)

**Infrastructure Models** (`app/models/infrastructure.py`)
- `PortData` - Complete port information
- `BerthData` - Berth with ships and equipment
- `BollardData` - Bollard with attached hooks

**Sensor Models** (`app/models/sensors.py`)
- `HookData` - Hook tension with quality metrics
- `RadarData` - Distance monitoring data

**Communication Models** (`app/models/communication.py`)
- `CrewMember` - Crew information and status
- `Alert` - System alerts with metadata
- `CommunicationMessage` - Multi-channel messages

**Analysis Models** (`app/models/analysis.py`)
- `ShipMovement` - Complete movement analysis
- `TensionPrediction` - Tension forecasting
- `Position3D` - 3D positioning data

### API Layer (Route Organization)

**Dashboard Routes** (`app/api/dashboard.py`)
- HTML page serving with template rendering
- Integration with services for data provision

**Data Routes** (`app/api/data.py`)
- Data reception from external generators
- Latest data retrieval and system statistics

**Monitoring Routes** (`app/api/monitoring.py`)
- Real-time alerts and system health
- Enhanced tension analysis endpoints

**Movement Routes** (`app/api/movements.py`)
- Ship movement analysis and 3D visualization
- Movement predictions and risk assessment

**Communication Routes** (`app/api/communication.py`)
- Crew communication and alert management
- Manual operations and response tracking

## 🔄 Migration Benefits

### From Monolithic (`dashboard.py`) to Modular

**Before (Single File):**
- ❌ 1000+ lines in one file
- ❌ Mixed concerns (UI, business logic, data handling)
- ❌ Difficult to test and maintain
- ❌ Hard to add new features
- ❌ No clear separation between components

**After (Modular Architecture):**
- ✅ Organized into logical modules
- ✅ Clear separation of concerns
- ✅ Easy to test individual components
- ✅ Simple to add new features
- ✅ Professional development practices

### Development Workflow Improvements

**Adding New Features:**
1. Add data models in `app/models/`
2. Implement business logic in `app/services/`
3. Create API endpoints in `app/api/`
4. Update configuration if needed in `app/core/`

**Testing Components:**
- Services can be unit tested independently
- Models validate data automatically
- API routes can be tested with FastAPI test client

**Maintenance:**
- Bug fixes are contained to specific modules
- Code changes don't affect unrelated functionality
- Clear dependency relationships

## 🎯 Running the New Application

### Development Mode
```bash
python main.py
```

### With Custom Configuration
```bash
export LOG_LEVEL=DEBUG
export PORT=8080
python main.py
```

### Production Deployment
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 🤝 Development Guidelines

### Adding New Models
```python
# app/models/new_feature.py
from pydantic import BaseModel

class NewFeature(BaseModel):
    name: str
    value: float
```

### Creating New Services
```python
# app/services/new_service.py
from ..models import NewFeature

class NewService:
    def __init__(self):
        self.data = {}
    
    def process_feature(self, feature: NewFeature):
        # Business logic here
        pass
```

### Adding API Routes
```python
# app/api/new_routes.py
from fastapi import APIRouter

router = APIRouter(prefix="/api")

@router.get("/new-endpoint")
async def get_new_data():
    return {"status": "success"}
```

## 📋 Next Steps

1. **Test the new modular application:**
   ```bash
   python main.py
   ```

2. **Verify all endpoints work:**
   - Visit http://127.0.0.1:8000/docs for API documentation
   - Test dashboard pages: `/`, `/monitoring`, `/ship-3d`

3. **Optional: Remove old files:**
   ```bash
   # After confirming everything works
   mv dashboard.py dashboard.py.backup
   mv enhanced_tension_monitor.py enhanced_tension_monitor.py.backup  
   mv ship_movement_analyzer.py ship_movement_analyzer.py.backup
   ```

4. **Start using the new architecture:**
   - All new features should be added using the modular structure
   - Follow the established patterns for consistency

## 📝 Summary

This restructure transforms a single 1000+ line file into a professional, maintainable application with:

- **Clear separation of concerns**
- **Testable and reusable components**  
- **Type-safe data handling**
- **Professional development practices**
- **Easy feature addition and maintenance**

You now have a proper application structure that can grow and be maintained easily! 🚀
#!/usr/bin/env python3
"""
Ship-Side Data Client for BHP Mooring System
Collects sensor data from ship systems and pushes to dashboard API
"""

import asyncio
import json
import time
import random
import math
from datetime import datetime, timedelta
import httpx
from typing import Dict, List, Optional
import logging
from dataclasses import dataclass
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ship_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SensorConfig:
    """Configuration for sensor interfaces"""
    modbus_port: str = "/dev/ttyUSB0"
    ethernet_sensors: List[str] = None
    dashboard_url: str = "http://127.0.0.1:8000/"
    update_interval: float = 2.0  # seconds
    ship_id: str = "MV_EXAMPLE"
    berth_name: str = "Berth A"

class SensorDataCollector:
    """Collects data from various ship sensor systems"""
    
    def __init__(self, config: SensorConfig):
        self.config = config
        self.is_running = False
        self.last_readings = {}
        
    async def read_tension_sensors(self) -> Dict:
        """Read tension data from hook sensors (simulated for demo)"""
        # In real implementation, this would interface with:
        # - Modbus RTU/TCP devices
        # - Ethernet-based load cells
        # - CAN bus sensors
        # - PLC data concentrators
        
        tensions = {}
        base_time = time.time()
        
        # Simulate 12 hooks across 3 bollards
        for bollard_num in range(1, 4):
            bollard_name = f"BOL{bollard_num:03d}"
            hooks = []
            
            for hook_num in range(1, 5):
                hook_name = f"Hook {hook_num}"
                
                # Simulate realistic tension patterns
                time_factor = base_time / 60.0  # Convert to minutes
                base_tension = 40 + 30 * math.sin(time_factor * 0.1 + hook_num)
                noise = random.uniform(-5, 5)
                tension = max(0, min(100, base_tension + noise))
                
                # Simulate occasional sensor issues
                sensor_quality = random.choices(
                    ['excellent', 'good', 'fair', 'poor'],
                    weights=[40, 50, 8, 2]
                )[0]
                
                confidence = random.uniform(0.85, 1.0) if sensor_quality != 'poor' else random.uniform(0.3, 0.7)
                
                # Determine line type based on position
                line_types = ['BREAST', 'SPRING', 'BOW', 'STERN']
                attached_line = line_types[hook_num % len(line_types)]
                
                hook_data = {
                    "name": hook_name,
                    "tension": int(tension),
                    "faulted": sensor_quality == 'poor' and random.random() < 0.1,
                    "attachedLine": attached_line,
                    "sensor_quality": sensor_quality,
                    "confidence_score": round(confidence, 3),
                    "calibration_date": (datetime.now() - timedelta(days=random.randint(1, 90))).isoformat(),
                    "environmental_factors": {
                        "wind_speed": random.uniform(5, 25),
                        "wave_height": random.uniform(0.5, 3.0),
                        "temperature": random.uniform(15, 35)
                    }
                }
                hooks.append(hook_data)
            
            tensions[bollard_name] = hooks
        
        return tensions
    
    async def read_radar_data(self) -> List[Dict]:
        """Read radar/proximity sensor data"""
        # In real implementation: Interface with radar systems
        radars = []
        
        for radar_num in range(1, 3):
            radar_name = f"BARD{radar_num}"
            
            # Simulate ship distance measurements
            base_distance = 15.0 + random.uniform(-2, 2)
            distance_change = random.uniform(-0.5, 0.5)
            
            radar_data = {
                "name": radar_name,
                "shipDistance": round(base_distance, 1),
                "distanceChange": round(distance_change, 1),
                "distanceStatus": "ACTIVE" if base_distance < 50 else "INACTIVE"
            }
            radars.append(radar_data)
        
        return radars
    
    async def read_ship_data(self) -> Dict:
        """Read ship identification and status"""
        return {
            "name": "MV Iron Duke",
            "vesselId": self.config.ship_id
        }
    
    async def collect_all_sensor_data(self) -> Dict:
        """Collect data from all sensor systems"""
        try:
            # Collect from all sensor types
            tension_data = await self.read_tension_sensors()
            radar_data = await self.read_radar_data()
            ship_data = await self.read_ship_data()
            
            # Build bollard structure
            bollards = []
            for bollard_name, hooks in tension_data.items():
                bollards.append({
                    "name": bollard_name,
                    "hooks": hooks
                })
            
            # Construct complete data structure
            berth_data = {
                "name": self.config.berth_name,
                "bollardCount": len(bollards),
                "hookCount": sum(len(b["hooks"]) for b in bollards),
                "ship": ship_data,
                "radars": radar_data,
                "bollards": bollards
            }
            
            complete_data = {
                "name": "Port Hedland",
                "berths": [berth_data]
            }
            
            logger.debug(f"Collected data: {len(bollards)} bollards, {sum(len(b['hooks']) for b in bollards)} hooks")
            return complete_data
            
        except Exception as e:
            logger.error(f"Error collecting sensor data: {e}")
            return None

class DashboardCommunicator:
    """Handles communication with the dashboard API"""
    
    def __init__(self, dashboard_url: str):
        self.dashboard_url = dashboard_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=10.0)
        self.consecutive_failures = 0
        self.max_failures = 5
        
    async def send_data(self, data: Dict) -> bool:
        """Send sensor data to dashboard"""
        try:
            response = await self.client.post(
                f"{self.dashboard_url}/",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                self.consecutive_failures = 0
                logger.debug("Data sent successfully to dashboard")
                return True
            else:
                logger.warning(f"Dashboard returned status {response.status_code}")
                self.consecutive_failures += 1
                return False
                
        except httpx.ConnectError:
            self.consecutive_failures += 1
            if self.consecutive_failures <= 3:
                logger.warning(f"Connection failed to dashboard (attempt {self.consecutive_failures})")
            return False
        except Exception as e:
            logger.error(f"Error sending data to dashboard: {e}")
            self.consecutive_failures += 1
            return False
    
    async def check_dashboard_health(self) -> bool:
        """Check if dashboard is responsive"""
        try:
            response = await self.client.get(f"{self.dashboard_url}/api/latest")
            return response.status_code == 200
        except:
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

class ShipDataClient:
    """Main ship data client orchestrator"""
    
    def __init__(self, config: SensorConfig):
        self.config = config
        self.sensor_collector = SensorDataCollector(config)
        self.dashboard_comm = DashboardCommunicator(config.dashboard_url)
        self.is_running = False
        self._setup_signal_handlers()
        
    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self.is_running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_continuous(self):
        """Main continuous data collection and transmission loop"""
        logger.info(f"Starting ship data client for {self.config.ship_id}")
        logger.info(f"Dashboard URL: {self.config.dashboard_url}")
        logger.info(f"Update interval: {self.config.update_interval} seconds")
        
        self.is_running = True
        
        # Check dashboard connectivity
        if not await self.dashboard_comm.check_dashboard_health():
            logger.warning("Dashboard is not responding - starting anyway...")
        
        transmission_count = 0
        
        try:
            while self.is_running:
                start_time = time.time()
                
                # Collect sensor data
                sensor_data = await self.sensor_collector.collect_all_sensor_data()
                
                if sensor_data:
                    # Send to dashboard
                    success = await self.dashboard_comm.send_data(sensor_data)
                    
                    if success:
                        transmission_count += 1
                        if transmission_count % 30 == 0:  # Log every 30 transmissions (~1 minute)
                            logger.info(f"Successfully transmitted {transmission_count} data packets")
                    else:
                        if self.dashboard_comm.consecutive_failures >= self.dashboard_comm.max_failures:
                            logger.error("Too many consecutive failures - check dashboard connectivity")
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, self.config.update_interval - elapsed)
                
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(f"Data collection taking longer than interval: {elapsed:.2f}s")
        
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
        
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Shutting down ship data client...")
        await self.dashboard_comm.close()
        logger.info("Shutdown complete")

async def main():
    """Main entry point"""
    # Configuration
    config = SensorConfig(
        dashboard_url="http://127.0.0.1:8000/",
        update_interval=2.0,
        ship_id="MV_IRON_DUKE_001",
        berth_name="Berth A"
    )
    
    # Create and run client
    client = ShipDataClient(config)
    await client.run_continuous()

if __name__ == "__main__":
    print("🚢 BHP Ship Data Client")
    print("======================")
    print("Collecting sensor data and transmitting to dashboard...")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Ship data client stopped by user")
    except Exception as e:
        print(f"\n❌ Ship data client crashed: {e}")
        sys.exit(1)
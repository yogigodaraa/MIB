"""
Movement Analysis Service
Service for analyzing ship movements in 3D space.
"""

import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ..models import (
    ShipMovement, MovementVector, Position3D, MovementAnalysis, 
    MovementPrediction, BerthData
)


class MovementAnalysisService:
    """Service for analyzing and calculating ship movements in 3D space"""
    
    def __init__(self):
        self.movement_history = {}
        self.position_cache = {}
        
    def analyze_3d_movement(self, berth_data: dict, berth_name: str) -> ShipMovement:
        """Analyze ship movement in 3D space"""
        try:
            if not berth_data:
                berth_data = {}
            
            # Extract radar positions and hook tensions
            radar_positions = self._extract_radar_positions(berth_data.get('radars', []) or [])
            hook_positions = self._extract_hook_positions(berth_data.get('bollards', []) or [])
        
            # Calculate 3D position
            current_position = self._calculate_3d_position(radar_positions, hook_positions)
            
            # Store position history
            position_key = f"position_{berth_name}"
            if position_key not in self.movement_history:
                self.movement_history[position_key] = []
                
            self.movement_history[position_key].append({
                'timestamp': datetime.now().isoformat(),
                'position': current_position,
                'radar_data': radar_positions,
                'hook_data': hook_positions
            })
            
            # Keep only last 20 positions
            if len(self.movement_history[position_key]) > 20:
                self.movement_history[position_key] = self.movement_history[position_key][-20:]
            
            # Calculate movement vectors
            movement_vector = self._calculate_movement_vector(position_key)
            
            # Analyze movement patterns
            movement_analysis = self._analyze_movement_patterns(position_key)
            
            # Predict future movement
            movement_prediction = self._predict_3d_movement(position_key, movement_vector)
            
            return ShipMovement(
                berth_name=berth_name,
                ship_name=berth_data.get('ship', {}).get('name', 'Unknown'),
                current_position=current_position,
                movement_vector=movement_vector,
                movement_analysis=movement_analysis,
                movement_prediction=movement_prediction,
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"Error in analyze_3d_movement: {e}")
            # Return a safe default movement object
            return ShipMovement(
                berth_name=berth_name,
                ship_name='Unknown',
                current_position=Position3D(x=0, y=0, z=0),
                movement_vector=MovementVector(x=0, y=0, z=0),
                movement_analysis=MovementAnalysis(
                    displacement=0,
                    velocity=0,
                    acceleration=0,
                    direction=0
                ),
                movement_prediction=MovementPrediction(
                    predicted_position=Position3D(x=0, y=0, z=0),
                    confidence=0
                ),
                timestamp=datetime.now()
            )
    
    def _extract_radar_positions(self, radars: List[dict]) -> Dict[str, dict]:
        """Extract radar positions and create a spatial map"""
        positions = {}
        
        if not radars:
            return positions
            
        for i, radar in enumerate(radars):
            if not radar or 'name' not in radar:
                continue
            # Simulate radar positions around the berth
            angle = (i / len(radars)) * 360 if len(radars) > 0 else 0
            radar_x = math.cos(math.radians(angle))
            radar_y = math.sin(math.radians(angle))
            
            positions[radar['name']] = {
                'x': radar_x,
                'y': radar_y,
                'distance': radar.get('shipDistance', 0) or 0,
                'distance_change': radar.get('distanceChange', 0) or 0,
                'status': radar.get('distanceStatus', 'INACTIVE'),
                'angle': angle
            }
            
        return positions
    
    def _extract_hook_positions(self, bollards: List[dict]) -> Dict[str, dict]:
        """Extract hook positions and tensions for spatial analysis"""
        positions = {}
        
        for bollard in bollards:
            if not bollard or 'name' not in bollard:
                continue
            bollard_name = bollard['name']
            
            for hook in bollard.get('hooks', []):
                if not hook or 'name' not in hook:
                    continue
                hook_id = f"{bollard_name}_{hook['name']}"
                attached_line = hook.get('attachedLine', '') or ''
                line_type = attached_line.upper()
                
                # Determine hook position based on line type
                position = self._get_hook_spatial_position(line_type, bollard_name)
                
                positions[hook_id] = {
                    'x': position[0],
                    'y': position[1],
                    'z': position[2],
                    'tension': hook.get('tension', 0),
                    'faulted': hook.get('faulted', False),
                    'line_type': line_type,
                    'bollard': bollard_name
                }
                
        return positions
    
    def _get_hook_spatial_position(self, line_type: str, bollard_name: str) -> Tuple[float, float, float]:
        """Get 3D spatial position of hook based on line type"""
        x, y, z = 0.0, 0.0, 0.0
        
        # Bow/Forward lines
        if any(keyword in line_type for keyword in ['BOW', 'FORWARD', 'HEAD']):
            x = -1.0  # Forward
        # Stern/Aft lines  
        elif any(keyword in line_type for keyword in ['STERN', 'AFT', 'TAIL']):
            x = 1.0   # Aft
        # Port side lines
        elif any(keyword in line_type for keyword in ['PORT', 'LEFT']):
            y = -1.0  # Port side
        # Starboard side lines
        elif any(keyword in line_type for keyword in ['STARBOARD', 'RIGHT']):
            y = 1.0   # Starboard side
        # Breast lines (perpendicular to ship)
        elif 'BREAST' in line_type:
            y = 0.5 if 'STARBOARD' in bollard_name.upper() else -0.5
        # Spring lines (diagonal)
        elif 'SPRING' in line_type:
            x = 0.5 if 'AFT' in line_type else -0.5
            y = 0.3 if 'STARBOARD' in bollard_name.upper() else -0.3
        
        # Add vertical component based on bollard position
        if 'UPPER' in bollard_name.upper():
            z = 0.5
        elif 'LOWER' in bollard_name.upper():
            z = -0.5
            
        return (x, y, z)
    
    def _calculate_3d_position(self, radar_positions: dict, hook_positions: dict) -> Position3D:
        """Calculate ship's 3D position relative to berth"""
        position_data = []
        
        # Calculate position from radar data
        for radar_name, radar in radar_positions.items():
            if radar['status'] == 'ACTIVE' and radar['distance'] > 0:
                x = radar['distance'] * radar['x']
                y = radar['distance'] * radar['y']
                position_data.append((x, y, 0.0, 0.8))  # High confidence for radar
        
        # Calculate position from hook tensions
        if hook_positions:
            x_tensions, y_tensions, z_tensions = [], [], []
            
            for hook_id, hook in hook_positions.items():
                tension = hook.get('tension', 0)
                if tension is None:
                    tension = 0
                faulted = hook.get('faulted', False)
                if not faulted and tension > 0:
                    tension_factor = tension / 100.0
                    
                    x_tensions.append(hook.get('x', 0) * tension_factor)
                    y_tensions.append(hook.get('y', 0) * tension_factor) 
                    z_tensions.append(hook.get('z', 0) * tension_factor)
            
            if x_tensions and y_tensions:
                avg_x = -sum(x_tensions) / len(x_tensions)
                avg_y = -sum(y_tensions) / len(y_tensions)
                avg_z = sum(z_tensions) / len(z_tensions) if z_tensions else 0.0
                
                position_data.append((avg_x * 10, avg_y * 10, avg_z * 5, 0.6))
        
        # Calculate weighted average position
        if position_data:
            total_weight = sum(weight for _, _, _, weight in position_data)
            
            x = sum(x * weight for x, _, _, weight in position_data) / total_weight
            y = sum(y * weight for _, y, _, weight in position_data) / total_weight
            z = sum(z * weight for _, _, z, weight in position_data) / total_weight
            distance = math.sqrt(x**2 + y**2 + z**2)
            confidence = min(1.0, total_weight / len(position_data))
            
            return Position3D(x=x, y=y, z=z, distance=distance, confidence=confidence)
        
        return Position3D()
    
    def _calculate_movement_vector(self, position_key: str) -> MovementVector:
        """Calculate movement vector from recent positions"""
        if position_key not in self.movement_history or len(self.movement_history[position_key]) < 2:
            return MovementVector()
        
        history = self.movement_history[position_key]
        recent_positions = history[-5:]
        
        if len(recent_positions) >= 2:
            start_pos = recent_positions[0]['position']
            end_pos = recent_positions[-1]['position']
            
            dx = end_pos['x'] - start_pos['x']
            dy = end_pos['y'] - start_pos['y'] 
            dz = end_pos['z'] - start_pos['z']
            speed = math.sqrt(dx**2 + dy**2 + dz**2)
            
            # Determine primary direction
            abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)
            
            if max(abs_dx, abs_dy, abs_dz) < 0.1:
                direction = 'stable'
            elif abs_dx > abs_dy and abs_dx > abs_dz:
                direction = 'forward' if dx < 0 else 'backward'
            elif abs_dy > abs_dz:
                direction = 'port' if dy < 0 else 'starboard'
            else:
                direction = 'up' if dz > 0 else 'down'
            
            # Calculate confidence
            position_confidence = min(pos['position']['confidence'] for pos in recent_positions)
            confidence = position_confidence * min(1.0, len(recent_positions) / 5.0)
            
            return MovementVector(
                dx=dx, dy=dy, dz=dz, 
                speed=speed, direction=direction, confidence=confidence
            )
        
        return MovementVector()
    
    def _analyze_movement_patterns(self, position_key: str) -> MovementAnalysis:
        """Analyze movement patterns for insights"""
        if position_key not in self.movement_history or len(self.movement_history[position_key]) < 5:
            return MovementAnalysis()
        
        history = self.movement_history[position_key]
        positions = [pos['position'] for pos in history]
        
        # Calculate position variance
        x_values = [pos['x'] for pos in positions]
        y_values = [pos['y'] for pos in positions]
        z_values = [pos['z'] for pos in positions]
        
        if len(x_values) > 1:
            x_std = statistics.stdev(x_values)
            y_std = statistics.stdev(y_values)
            z_std = statistics.stdev(z_values)
            
            total_variance = x_std + y_std + z_std
            
            # Determine movement pattern
            if total_variance > 5.0:
                pattern = 'erratic'
                risk_assessment = 'high'
                movement_intensity = 'high'
            elif total_variance > 2.0:
                pattern = 'active'
                risk_assessment = 'medium'
                movement_intensity = 'medium'
            else:
                pattern = 'stable'
                risk_assessment = 'low'
                movement_intensity = 'low'
            
            # Check for oscillation
            oscillation = False
            if len(positions) >= 6:
                direction_changes = 0
                for i in range(2, len(x_values)):
                    if (x_values[i] - x_values[i-1]) * (x_values[i-1] - x_values[i-2]) < 0:
                        direction_changes += 1
                oscillation = direction_changes > len(x_values) * 0.3
            
            # Determine drift direction
            drift_direction = None
            x_trend = x_values[-1] - x_values[0]
            y_trend = y_values[-1] - y_values[0]
            
            if abs(x_trend) > 1.0 or abs(y_trend) > 1.0:
                if abs(x_trend) > abs(y_trend):
                    drift_direction = 'aft' if x_trend > 0 else 'forward'
                else:
                    drift_direction = 'starboard' if y_trend > 0 else 'port'
            
            # Calculate stability score
            stability_score = max(0, min(100, int(100 - (total_variance * 10))))
            
            return MovementAnalysis(
                pattern=pattern,
                oscillation=oscillation,
                drift_direction=drift_direction,
                stability_score=stability_score,
                risk_assessment=risk_assessment,
                movement_intensity=movement_intensity
            )
        
        return MovementAnalysis()
    
    def _predict_3d_movement(self, position_key: str, movement_vector: MovementVector) -> MovementPrediction:
        """Predict future 3D movement"""
        if position_key not in self.movement_history:
            return MovementPrediction(predicted_position=Position3D())
        
        current_pos = self.movement_history[position_key][-1]['position']
        
        # Predict position in 2 minutes
        time_factor = 24  # 2 minutes at 5-second intervals
        
        predicted_pos = Position3D(
            x=current_pos['x'] + (movement_vector.dx * time_factor),
            y=current_pos['y'] + (movement_vector.dy * time_factor),
            z=current_pos['z'] + (movement_vector.dz * time_factor)
        )
        
        warnings = []
        recommendations = []
        
        # Generate warnings and recommendations
        pred_distance = math.sqrt(predicted_pos.x**2 + predicted_pos.y**2 + predicted_pos.z**2)
        
        if pred_distance > 50:
            warnings.append("🚨 Ship predicted to drift beyond safe distance")
            recommendations.append("Consider tightening mooring lines")
        
        if abs(predicted_pos.y) > 20:
            side = "starboard" if predicted_pos.y > 0 else "port"
            warnings.append(f"⚠️ Lateral drift detected towards {side} side")
            recommendations.append(f"Check {side} side mooring lines")
        
        if movement_vector.speed > 2.0:
            warnings.append("🔴 High movement speed detected")
            recommendations.append("Monitor environmental conditions and mooring status")
        
        return MovementPrediction(
            predicted_position=predicted_pos,
            confidence=movement_vector.confidence,
            warnings=warnings,
            recommendations=recommendations
        )

    def get_movement_summary(self) -> dict:
        """Get summary of all ship movements"""
        summary = {
            'total_ships': len(self.movement_history),
            'active_movements': 0,
            'high_risk_ships': [],
            'system_status': 'operational'
        }
        
        for position_key, history in self.movement_history.items():
            if history and len(history) > 0:
                latest = history[-1]
                berth_name = position_key.replace('position_', '')
                
                # Check if movement is significant
                if len(history) >= 2:
                    prev_pos = history[-2]['position']
                    curr_pos = latest['position']
                    
                    movement_distance = math.sqrt(
                        (curr_pos['x'] - prev_pos['x'])**2 +
                        (curr_pos['y'] - prev_pos['y'])**2 +
                        (curr_pos['z'] - prev_pos['z'])**2
                    )
                    
                    if movement_distance > 0.5:
                        summary['active_movements'] += 1
                    
                    if movement_distance > 2.0 or curr_pos['distance'] > 30:
                        summary['high_risk_ships'].append({
                            'berth': berth_name,
                            'distance': curr_pos['distance'],
                            'movement_speed': movement_distance
                        })
        
        if summary['high_risk_ships']:
            summary['system_status'] = 'warning' if len(summary['high_risk_ships']) == 1 else 'critical'
        
        return summary
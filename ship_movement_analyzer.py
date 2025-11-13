#!/usr/bin/env python3
"""
Ship Movement Analyzer
Dedicated module for analyzing and calculating ship movements in 3D space
"""

import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

class ShipMovementAnalyzer:
    def __init__(self):
        self.movement_history = {}
        self.position_cache = {}
        
    def analyze_3d_movement(self, berth_data: dict, berth_name: str) -> dict:
        """Analyze ship movement in 3D space (forward/back, left/right, up/down)"""
        
        # Extract radar positions and hook tensions
        radar_positions = self._extract_radar_positions(berth_data.get('radars', []))
        hook_positions = self._extract_hook_positions(berth_data.get('bollards', []))
        
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
        
        return {
            'berth_name': berth_name,
            'ship_name': berth_data.get('ship', {}).get('name', 'Unknown'),
            'current_position': current_position,
            'movement_vector': movement_vector,
            'movement_analysis': movement_analysis,
            'movement_prediction': movement_prediction,
            'radar_positions': radar_positions,
            'hook_positions': hook_positions,
            'position_history': self.movement_history[position_key][-10:],  # Last 10 positions
            'timestamp': datetime.now().isoformat()
        }
    
    def _extract_radar_positions(self, radars: List[dict]) -> Dict[str, dict]:
        """Extract radar positions and create a spatial map"""
        positions = {}
        
        for i, radar in enumerate(radars):
            # Simulate radar positions around the berth
            angle = (i / len(radars)) * 360 if radars else 0
            radar_x = math.cos(math.radians(angle))
            radar_y = math.sin(math.radians(angle))
            
            positions[radar['name']] = {
                'x': radar_x,
                'y': radar_y,
                'distance': radar.get('shipDistance', 0),
                'distance_change': radar.get('distanceChange', 0),
                'status': radar.get('distanceStatus', 'INACTIVE'),
                'angle': angle
            }
            
        return positions
    
    def _extract_hook_positions(self, bollards: List[dict]) -> Dict[str, dict]:
        """Extract hook positions and tensions for spatial analysis"""
        positions = {}
        
        for bollard in bollards:
            bollard_name = bollard['name']
            
            for hook in bollard.get('hooks', []):
                hook_id = f"{bollard_name}_{hook['name']}"
                line_type = hook.get('attachedLine', '').upper()
                
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
        # Default position
        x, y, z = 0.0, 0.0, 0.0
        
        # Bow/Forward lines
        if any(keyword in line_type for keyword in ['BOW', 'FORWARD', 'HEAD']):
            x = -1.0  # Forward
            y = 0.0
            z = 0.0
        
        # Stern/Aft lines  
        elif any(keyword in line_type for keyword in ['STERN', 'AFT', 'TAIL']):
            x = 1.0   # Aft
            y = 0.0
            z = 0.0
        
        # Port side lines
        elif any(keyword in line_type for keyword in ['PORT', 'LEFT']):
            x = 0.0
            y = -1.0  # Port side
            z = 0.0
        
        # Starboard side lines
        elif any(keyword in line_type for keyword in ['STARBOARD', 'RIGHT']):
            x = 0.0
            y = 1.0   # Starboard side
            z = 0.0
        
        # Breast lines (perpendicular to ship)
        elif 'BREAST' in line_type:
            x = 0.0
            y = 0.5 if 'STARBOARD' in bollard_name.upper() else -0.5
            z = 0.0
        
        # Spring lines (diagonal)
        elif 'SPRING' in line_type:
            x = 0.5 if 'AFT' in line_type else -0.5
            y = 0.3 if 'STARBOARD' in bollard_name.upper() else -0.3
            z = 0.0
        
        # Add vertical component based on bollard position
        if 'UPPER' in bollard_name.upper():
            z = 0.5
        elif 'LOWER' in bollard_name.upper():
            z = -0.5
            
        return (x, y, z)
    
    def _calculate_3d_position(self, radar_positions: dict, hook_positions: dict) -> dict:
        """Calculate ship's 3D position relative to berth"""
        position = {
            'x': 0.0,  # Forward/Backward (negative = towards bow)
            'y': 0.0,  # Left/Right (negative = port, positive = starboard) 
            'z': 0.0,  # Up/Down (positive = up)
            'distance': 0.0,  # Overall distance from berth
            'confidence': 0.0
        }
        
        position_data = []
        
        # Calculate position from radar data
        for radar_name, radar in radar_positions.items():
            if radar['status'] == 'ACTIVE' and radar['distance'] > 0:
                # Convert radar distance to X,Y coordinates
                x = radar['distance'] * radar['x']
                y = radar['distance'] * radar['y']
                position_data.append((x, y, 0.0, 0.8))  # High confidence for radar
        
        # Calculate position from hook tensions (indirect method)
        if hook_positions:
            x_tensions, y_tensions, z_tensions = [], [], []
            
            for hook_id, hook in hook_positions.items():
                if not hook['faulted'] and hook['tension'] > 0:
                    # Higher tension indicates ship pulling away from that direction
                    tension_factor = hook['tension'] / 100.0
                    
                    x_tensions.append(hook['x'] * tension_factor)
                    y_tensions.append(hook['y'] * tension_factor) 
                    z_tensions.append(hook['z'] * tension_factor)
            
            if x_tensions and y_tensions:
                # Average tension-based position (inverted because tension indicates pull)
                avg_x = -sum(x_tensions) / len(x_tensions)
                avg_y = -sum(y_tensions) / len(y_tensions)
                avg_z = sum(z_tensions) / len(z_tensions) if z_tensions else 0.0
                
                position_data.append((avg_x * 10, avg_y * 10, avg_z * 5, 0.6))  # Lower confidence
        
        # Calculate weighted average position
        if position_data:
            total_weight = sum(weight for _, _, _, weight in position_data)
            
            position['x'] = sum(x * weight for x, _, _, weight in position_data) / total_weight
            position['y'] = sum(y * weight for _, y, _, weight in position_data) / total_weight
            position['z'] = sum(z * weight for _, _, z, weight in position_data) / total_weight
            position['distance'] = math.sqrt(position['x']**2 + position['y']**2 + position['z']**2)
            position['confidence'] = min(1.0, total_weight / len(position_data))
        
        return position
    
    def _calculate_movement_vector(self, position_key: str) -> dict:
        """Calculate movement vector from recent positions"""
        vector = {
            'dx': 0.0,      # X movement (forward/back)
            'dy': 0.0,      # Y movement (left/right)  
            'dz': 0.0,      # Z movement (up/down)
            'speed': 0.0,   # Overall speed
            'direction': 'stable',
            'confidence': 0.0
        }
        
        if position_key not in self.movement_history or len(self.movement_history[position_key]) < 2:
            return vector
        
        history = self.movement_history[position_key]
        
        # Calculate movement over last 5 positions
        recent_positions = history[-5:]
        if len(recent_positions) >= 2:
            start_pos = recent_positions[0]['position']
            end_pos = recent_positions[-1]['position']
            
            vector['dx'] = end_pos['x'] - start_pos['x']
            vector['dy'] = end_pos['y'] - start_pos['y'] 
            vector['dz'] = end_pos['z'] - start_pos['z']
            vector['speed'] = math.sqrt(vector['dx']**2 + vector['dy']**2 + vector['dz']**2)
            
            # Determine primary direction
            abs_dx, abs_dy, abs_dz = abs(vector['dx']), abs(vector['dy']), abs(vector['dz'])
            
            if max(abs_dx, abs_dy, abs_dz) < 0.1:
                vector['direction'] = 'stable'
            elif abs_dx > abs_dy and abs_dx > abs_dz:
                vector['direction'] = 'forward' if vector['dx'] < 0 else 'backward'
            elif abs_dy > abs_dz:
                vector['direction'] = 'port' if vector['dy'] < 0 else 'starboard'
            else:
                vector['direction'] = 'up' if vector['dz'] > 0 else 'down'
            
            # Calculate confidence based on position consistency
            position_confidence = min(pos['position']['confidence'] for pos in recent_positions)
            vector['confidence'] = position_confidence * min(1.0, len(recent_positions) / 5.0)
        
        return vector
    
    def _analyze_movement_patterns(self, position_key: str) -> dict:
        """Analyze movement patterns for insights"""
        analysis = {
            'pattern': 'stable',
            'oscillation': False,
            'drift_direction': None,
            'stability_score': 85,
            'risk_assessment': 'low',
            'movement_intensity': 'minimal'
        }
        
        if position_key not in self.movement_history or len(self.movement_history[position_key]) < 5:
            return analysis
        
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
            
            # Determine movement pattern
            total_variance = x_std + y_std + z_std
            
            if total_variance > 5.0:
                analysis['pattern'] = 'erratic'
                analysis['risk_assessment'] = 'high'
                analysis['movement_intensity'] = 'high'
            elif total_variance > 2.0:
                analysis['pattern'] = 'active'
                analysis['risk_assessment'] = 'medium'
                analysis['movement_intensity'] = 'medium'
            else:
                analysis['pattern'] = 'stable'
                analysis['movement_intensity'] = 'low'
            
            # Check for oscillation
            if len(positions) >= 6:
                direction_changes = 0
                for i in range(2, len(x_values)):
                    if (x_values[i] - x_values[i-1]) * (x_values[i-1] - x_values[i-2]) < 0:
                        direction_changes += 1
                
                analysis['oscillation'] = direction_changes > len(x_values) * 0.3
            
            # Determine drift direction
            x_trend = x_values[-1] - x_values[0]
            y_trend = y_values[-1] - y_values[0]
            
            if abs(x_trend) > 1.0 or abs(y_trend) > 1.0:
                if abs(x_trend) > abs(y_trend):
                    analysis['drift_direction'] = 'aft' if x_trend > 0 else 'forward'
                else:
                    analysis['drift_direction'] = 'starboard' if y_trend > 0 else 'port'
            
            # Calculate stability score
            analysis['stability_score'] = max(0, min(100, int(100 - (total_variance * 10))))
        
        return analysis
    
    def _predict_3d_movement(self, position_key: str, movement_vector: dict) -> dict:
        """Predict future 3D movement"""
        prediction = {
            'predicted_position': {'x': 0, 'y': 0, 'z': 0},
            'time_horizon': '2_minutes',
            'confidence': 0.5,
            'warnings': [],
            'recommendations': []
        }
        
        if position_key not in self.movement_history:
            return prediction
        
        current_pos = self.movement_history[position_key][-1]['position']
        
        # Predict position in 2 minutes based on current vector
        time_factor = 24  # 2 minutes at 5-second intervals
        
        prediction['predicted_position'] = {
            'x': current_pos['x'] + (movement_vector['dx'] * time_factor),
            'y': current_pos['y'] + (movement_vector['dy'] * time_factor),
            'z': current_pos['z'] + (movement_vector['dz'] * time_factor)
        }
        
        prediction['confidence'] = movement_vector['confidence']
        
        # Generate warnings and recommendations
        pred_distance = math.sqrt(
            prediction['predicted_position']['x']**2 + 
            prediction['predicted_position']['y']**2 + 
            prediction['predicted_position']['z']**2
        )
        
        if pred_distance > 50:
            prediction['warnings'].append("🚨 Ship predicted to drift beyond safe distance")
            prediction['recommendations'].append("Consider tightening mooring lines")
        
        if abs(prediction['predicted_position']['y']) > 20:
            side = "starboard" if prediction['predicted_position']['y'] > 0 else "port"
            prediction['warnings'].append(f"⚠️ Lateral drift detected towards {side} side")
            prediction['recommendations'].append(f"Check {side} side mooring lines")
        
        if movement_vector['speed'] > 2.0:
            prediction['warnings'].append("🔴 High movement speed detected")
            prediction['recommendations'].append("Monitor environmental conditions and mooring status")
        
        return prediction

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
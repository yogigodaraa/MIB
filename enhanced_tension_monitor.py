#!/usr/bin/env python3
"""
Enhanced Tension Monitoring System
Advanced accuracy improvements for hook tension monitoring
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

logger = logging.getLogger(__name__)

class EnhancedTensionMonitor:
    def __init__(self):
        self.sensor_data_buffer = {}  # Rolling buffer for each sensor
        self.sensor_calibration = {}  # Calibration data for each sensor
        self.environmental_data = {}  # Environmental factors affecting tension
        self.tension_baselines = {}   # Baseline tensions for each hook
        self.anomaly_detection = {}   # Anomaly detection for each sensor
        self.prediction_models = {}   # Predictive models for each hook
        
        # Accuracy thresholds
        self.accuracy_config = {
            'buffer_size': 50,           # Number of readings to keep
            'outlier_threshold': 2.5,    # Standard deviations for outlier detection
            'confidence_threshold': 0.7,  # Minimum confidence for readings
            'calibration_drift_limit': 5, # Max % drift before recalibration warning
            'smoothing_window': 5,       # Window for moving average
            'prediction_window': 10      # Window for predictions
        }
    
    def process_tension_reading(self, hook_id: str, raw_tension: float, 
                               sensor_metadata: dict = None) -> dict:
        """Process a raw tension reading with accuracy enhancements"""
        
        # Initialize sensor if new
        if hook_id not in self.sensor_data_buffer:
            self._initialize_sensor(hook_id)
        
        # Store raw reading with timestamp
        timestamp = datetime.now()
        raw_reading = {
            'value': raw_tension,
            'timestamp': timestamp,
            'metadata': sensor_metadata or {}
        }
        
        # Add to buffer
        self.sensor_data_buffer[hook_id].append(raw_reading)
        
        # Apply accuracy enhancements
        processed_reading = self._enhance_accuracy(hook_id, raw_reading)
        
        return processed_reading
    
    def _initialize_sensor(self, hook_id: str):
        """Initialize sensor data structures"""
        self.sensor_data_buffer[hook_id] = deque(maxlen=self.accuracy_config['buffer_size'])
        self.sensor_calibration[hook_id] = {
            'offset': 0.0,
            'scale_factor': 1.0,
            'last_calibration': datetime.now(),
            'drift_rate': 0.0,
            'baseline_established': False
        }
        self.anomaly_detection[hook_id] = {
            'baseline_mean': 0.0,
            'baseline_std': 0.0,
            'outlier_count': 0,
            'consecutive_outliers': 0
        }
    
    def _enhance_accuracy(self, hook_id: str, raw_reading: dict) -> dict:
        """Apply multiple accuracy enhancement techniques"""
        
        # 1. Outlier Detection and Filtering
        is_outlier, outlier_score = self._detect_outlier(hook_id, raw_reading['value'])
        
        # 2. Sensor Drift Compensation
        drift_corrected = self._compensate_drift(hook_id, raw_reading['value'])
        
        # 3. Environmental Compensation
        env_corrected = self._compensate_environmental(hook_id, drift_corrected, raw_reading['timestamp'])
        
        # 4. Smoothing and Noise Reduction
        smoothed_value = self._apply_smoothing(hook_id, env_corrected)
        
        # 5. Cross-validation with nearby sensors
        cross_validated = self._cross_validate(hook_id, smoothed_value)
        
        # 6. Calculate confidence score
        confidence = self._calculate_confidence(hook_id, raw_reading['value'], cross_validated, is_outlier)
        
        # 7. Predictive validation
        prediction_check = self._validate_prediction(hook_id, cross_validated)
        
        processed_reading = {
            'hook_id': hook_id,
            'raw_value': raw_reading['value'],
            'processed_value': cross_validated if confidence > self.accuracy_config['confidence_threshold'] else None,
            'confidence_score': confidence,
            'is_outlier': is_outlier,
            'outlier_score': outlier_score,
            'drift_correction': drift_corrected - raw_reading['value'],
            'environmental_correction': env_corrected - drift_corrected,
            'smoothing_applied': smoothed_value - env_corrected,
            'cross_validation_delta': cross_validated - smoothed_value,
            'prediction_validation': prediction_check,
            'timestamp': raw_reading['timestamp'],
            'quality_flags': self._generate_quality_flags(hook_id, confidence, is_outlier),
            'recommendations': self._generate_accuracy_recommendations(hook_id, confidence, is_outlier)
        }
        
        # Update baseline if needed
        self._update_baseline(hook_id, cross_validated, confidence)
        
        return processed_reading
    
    def _detect_outlier(self, hook_id: str, value: float) -> Tuple[bool, float]:
        """Advanced outlier detection using multiple methods"""
        
        buffer = self.sensor_data_buffer[hook_id]
        if len(buffer) < 5:
            return False, 0.0
        
        recent_values = [reading['value'] for reading in list(buffer)[-10:]]
        
        # Statistical outlier detection
        mean_val = statistics.mean(recent_values)
        std_val = statistics.stdev(recent_values) if len(recent_values) > 1 else 0
        
        z_score = abs(value - mean_val) / std_val if std_val > 0 else 0
        statistical_outlier = z_score > self.accuracy_config['outlier_threshold']
        
        # IQR outlier detection
        sorted_values = sorted(recent_values)
        q1 = sorted_values[len(sorted_values) // 4]
        q3 = sorted_values[3 * len(sorted_values) // 4]
        iqr = q3 - q1
        iqr_outlier = value < (q1 - 1.5 * iqr) or value > (q3 + 1.5 * iqr)
        
        # Rate of change outlier detection
        if len(buffer) >= 2:
            prev_value = buffer[-1]['value']
            rate_change = abs(value - prev_value)
            avg_rate = statistics.mean([abs(recent_values[i] - recent_values[i-1]) 
                                      for i in range(1, len(recent_values))])
            rate_outlier = rate_change > avg_rate * 3
        else:
            rate_outlier = False
        
        # Combined outlier decision
        is_outlier = statistical_outlier or iqr_outlier or rate_outlier
        outlier_score = max(z_score / self.accuracy_config['outlier_threshold'], 
                           rate_change / (avg_rate * 3) if 'avg_rate' in locals() and avg_rate > 0 else 0)
        
        # Update anomaly detection stats
        anomaly_data = self.anomaly_detection[hook_id]
        if is_outlier:
            anomaly_data['outlier_count'] += 1
            anomaly_data['consecutive_outliers'] += 1
        else:
            anomaly_data['consecutive_outliers'] = 0
        
        return is_outlier, outlier_score
    
    def _compensate_drift(self, hook_id: str, value: float) -> float:
        """Compensate for sensor drift over time"""
        calib_data = self.sensor_calibration[hook_id]
        
        # Calculate time since last calibration
        time_since_calib = datetime.now() - calib_data['last_calibration']
        hours_elapsed = time_since_calib.total_seconds() / 3600
        
        # Apply drift compensation
        drift_correction = calib_data['drift_rate'] * hours_elapsed
        corrected_value = (value + calib_data['offset'] - drift_correction) * calib_data['scale_factor']
        
        return corrected_value
    
    def _compensate_environmental(self, hook_id: str, value: float, timestamp: datetime) -> float:
        """Compensate for environmental factors affecting tension readings"""
        
        # Get environmental data (temperature, humidity, wind, etc.)
        env_factors = self.environmental_data.get(hook_id, {})
        
        # Temperature compensation (sensors drift with temperature)
        temp_compensation = 0.0
        if 'temperature' in env_factors:
            temp_delta = env_factors['temperature'] - 20  # Assume 20°C baseline
            temp_compensation = value * 0.001 * temp_delta  # 0.1% per degree
        
        # Humidity compensation (affects sensor readings)
        humidity_compensation = 0.0
        if 'humidity' in env_factors:
            humidity_delta = env_factors['humidity'] - 50  # Assume 50% baseline
            humidity_compensation = value * 0.0005 * humidity_delta
        
        # Wind load compensation (wind affects actual tension)
        wind_compensation = 0.0
        if 'wind_speed' in env_factors and 'wind_direction' in env_factors:
            wind_effect = self._calculate_wind_effect(hook_id, env_factors)
            wind_compensation = wind_effect
        
        compensated_value = value - temp_compensation - humidity_compensation + wind_compensation
        
        return compensated_value
    
    def _apply_smoothing(self, hook_id: str, value: float) -> float:
        """Apply smoothing to reduce noise while preserving rapid changes"""
        
        buffer = self.sensor_data_buffer[hook_id]
        if len(buffer) < self.accuracy_config['smoothing_window']:
            return value
        
        # Get recent processed values (exclude outliers)
        recent_values = []
        for reading in list(buffer)[-self.accuracy_config['smoothing_window']:]:
            if not self._detect_outlier(hook_id, reading['value'])[0]:
                recent_values.append(reading['value'])
        
        if not recent_values:
            return value
        
        # Exponential weighted moving average (more responsive to recent changes)
        alpha = 0.3  # Smoothing factor
        ema = recent_values[0]
        for val in recent_values[1:]:
            ema = alpha * val + (1 - alpha) * ema
        
        # Adaptive smoothing based on rate of change
        if len(recent_values) >= 2:
            rate_of_change = abs(recent_values[-1] - recent_values[-2])
            avg_rate = statistics.mean([abs(recent_values[i] - recent_values[i-1]) 
                                      for i in range(1, len(recent_values))])
            
            # Reduce smoothing during rapid changes
            if rate_of_change > avg_rate * 2:
                smoothing_factor = 0.7  # Less smoothing
            else:
                smoothing_factor = 0.3  # More smoothing
            
            smoothed_value = smoothing_factor * value + (1 - smoothing_factor) * ema
        else:
            smoothed_value = ema
        
        return smoothed_value
    
    def _cross_validate(self, hook_id: str, value: float) -> float:
        """Cross-validate with nearby sensors for consistency"""
        
        # Find related hooks (same bollard, similar line types)
        related_hooks = self._find_related_hooks(hook_id)
        
        if not related_hooks:
            return value
        
        # Get recent values from related hooks
        related_values = []
        for related_id in related_hooks:
            if related_id in self.sensor_data_buffer and self.sensor_data_buffer[related_id]:
                recent_reading = self.sensor_data_buffer[related_id][-1]
                related_values.append(recent_reading['value'])
        
        if not related_values:
            return value
        
        # Calculate expected value based on related sensors
        avg_related = statistics.mean(related_values)
        
        # Weight validation based on how many related sensors agree
        agreement_threshold = 15  # % difference threshold
        agreeing_sensors = sum(1 for rv in related_values 
                             if abs(rv - value) / max(rv, value, 1) * 100 < agreement_threshold)
        
        agreement_ratio = agreeing_sensors / len(related_values)
        
        # Apply weighted correction
        if agreement_ratio < 0.5:  # Less than half agree
            # Strong correction towards average
            corrected_value = 0.7 * avg_related + 0.3 * value
        elif agreement_ratio < 0.8:  # Some disagreement
            # Moderate correction
            corrected_value = 0.8 * value + 0.2 * avg_related
        else:  # Good agreement
            # Minimal correction
            corrected_value = 0.95 * value + 0.05 * avg_related
        
        return corrected_value
    
    def _find_related_hooks(self, hook_id: str) -> List[str]:
        """Find hooks that should have similar tension patterns"""
        # This would be implemented based on the actual hook naming convention
        # For now, return empty list
        return []
    
    def _calculate_confidence(self, hook_id: str, raw_value: float, 
                            processed_value: float, is_outlier: bool) -> float:
        """Calculate confidence score for the reading"""
        
        confidence_factors = []
        
        # Sensor health factor
        calib_data = self.sensor_calibration[hook_id]
        time_since_calib = datetime.now() - calib_data['last_calibration']
        days_since_calib = time_since_calib.days
        
        if days_since_calib < 7:
            confidence_factors.append(0.95)
        elif days_since_calib < 30:
            confidence_factors.append(0.85)
        elif days_since_calib < 90:
            confidence_factors.append(0.70)
        else:
            confidence_factors.append(0.50)
        
        # Outlier penalty
        if is_outlier:
            confidence_factors.append(0.30)
        else:
            confidence_factors.append(0.95)
        
        # Consistency with recent readings
        buffer = self.sensor_data_buffer[hook_id]
        if len(buffer) >= 5:
            recent_values = [reading['value'] for reading in list(buffer)[-5:]]
            std_recent = statistics.stdev(recent_values)
            if std_recent < 5:  # Low variance = high confidence
                confidence_factors.append(0.90)
            elif std_recent < 15:
                confidence_factors.append(0.75)
            else:
                confidence_factors.append(0.50)
        
        # Processing delta (large changes in processing suggest issues)
        processing_delta = abs(processed_value - raw_value) / max(raw_value, 1)
        if processing_delta < 0.05:  # < 5% change
            confidence_factors.append(0.95)
        elif processing_delta < 0.15:  # < 15% change
            confidence_factors.append(0.80)
        else:
            confidence_factors.append(0.60)
        
        # Calculate weighted average
        confidence = sum(confidence_factors) / len(confidence_factors)
        
        return min(1.0, max(0.0, confidence))
    
    def _validate_prediction(self, hook_id: str, current_value: float) -> dict:
        """Validate current reading against predictions"""
        
        validation = {
            'matches_prediction': True,
            'prediction_error': 0.0,
            'confidence_adjustment': 0.0
        }
        
        if hook_id not in self.prediction_models:
            return validation
        
        # Get prediction for this timestamp
        predicted_value = self._get_predicted_value(hook_id)
        
        if predicted_value is not None:
            prediction_error = abs(current_value - predicted_value) / max(predicted_value, 1)
            validation['prediction_error'] = prediction_error
            
            if prediction_error > 0.20:  # > 20% error
                validation['matches_prediction'] = False
                validation['confidence_adjustment'] = -0.15
            elif prediction_error > 0.10:  # > 10% error
                validation['confidence_adjustment'] = -0.05
            else:
                validation['confidence_adjustment'] = 0.05  # Boost confidence
        
        return validation
    
    def _get_predicted_value(self, hook_id: str) -> Optional[float]:
        """Get predicted value for current timestamp"""
        # Placeholder for prediction model
        return None
    
    def _generate_quality_flags(self, hook_id: str, confidence: float, is_outlier: bool) -> List[str]:
        """Generate quality flags for the reading"""
        flags = []
        
        if confidence < 0.5:
            flags.append("LOW_CONFIDENCE")
        
        if is_outlier:
            flags.append("OUTLIER_DETECTED")
        
        # Check sensor health
        calib_data = self.sensor_calibration[hook_id]
        days_since_calib = (datetime.now() - calib_data['last_calibration']).days
        
        if days_since_calib > 90:
            flags.append("CALIBRATION_OVERDUE")
        elif days_since_calib > 30:
            flags.append("CALIBRATION_DUE_SOON")
        
        # Check for consecutive outliers
        anomaly_data = self.anomaly_detection[hook_id]
        if anomaly_data['consecutive_outliers'] > 3:
            flags.append("SENSOR_DEGRADATION")
        
        return flags
    
    def _generate_accuracy_recommendations(self, hook_id: str, confidence: float, is_outlier: bool) -> List[str]:
        """Generate recommendations for improving accuracy"""
        recommendations = []
        
        if confidence < 0.7:
            recommendations.append("Consider sensor recalibration")
        
        if is_outlier:
            recommendations.append("Investigate sensor placement or environmental factors")
        
        anomaly_data = self.anomaly_detection[hook_id]
        if anomaly_data['consecutive_outliers'] > 5:
            recommendations.append("Urgent: Check sensor hardware and connections")
        
        calib_data = self.sensor_calibration[hook_id]
        if (datetime.now() - calib_data['last_calibration']).days > 60:
            recommendations.append("Schedule routine sensor maintenance")
        
        return recommendations
    
    def _update_baseline(self, hook_id: str, value: float, confidence: float):
        """Update baseline tension values for the hook"""
        
        if confidence < self.accuracy_config['confidence_threshold']:
            return
        
        anomaly_data = self.anomaly_detection[hook_id]
        
        if not self.sensor_calibration[hook_id]['baseline_established']:
            # Establish initial baseline
            buffer = self.sensor_data_buffer[hook_id]
            if len(buffer) >= 10:
                recent_values = [reading['value'] for reading in list(buffer)[-10:]]
                anomaly_data['baseline_mean'] = statistics.mean(recent_values)
                anomaly_data['baseline_std'] = statistics.stdev(recent_values)
                self.sensor_calibration[hook_id]['baseline_established'] = True
        else:
            # Update baseline with exponential decay
            alpha = 0.05  # Slow adaptation
            anomaly_data['baseline_mean'] = alpha * value + (1 - alpha) * anomaly_data['baseline_mean']
    
    def _calculate_wind_effect(self, hook_id: str, env_factors: dict) -> float:
        """Calculate wind effect on hook tension"""
        wind_speed = env_factors.get('wind_speed', 0)
        wind_direction = env_factors.get('wind_direction', 0)
        
        # Placeholder calculation - would need ship and hook geometry
        # Wind increases tension on windward side, decreases on leeward
        wind_factor = (wind_speed / 50.0) ** 2  # Quadratic relationship
        directional_factor = math.cos(math.radians(wind_direction))  # Simplified
        
        return wind_factor * directional_factor * 10  # Base wind effect
    
    def get_accuracy_summary(self) -> dict:
        """Get overall accuracy summary for all sensors"""
        summary = {
            'total_sensors': len(self.sensor_data_buffer),
            'high_confidence_sensors': 0,
            'medium_confidence_sensors': 0,
            'low_confidence_sensors': 0,
            'sensors_needing_attention': [],
            'overall_system_confidence': 0.0
        }
        
        confidence_scores = []
        
        for hook_id, buffer in self.sensor_data_buffer.items():
            if buffer:
                # Get latest reading confidence (would need to track this)
                latest_reading = buffer[-1]
                # Placeholder confidence calculation
                confidence = 0.8  
                
                confidence_scores.append(confidence)
                
                if confidence >= 0.8:
                    summary['high_confidence_sensors'] += 1
                elif confidence >= 0.6:
                    summary['medium_confidence_sensors'] += 1
                else:
                    summary['low_confidence_sensors'] += 1
                    summary['sensors_needing_attention'].append({
                        'hook_id': hook_id,
                        'confidence': confidence,
                        'issue': 'Low confidence readings'
                    })
        
        if confidence_scores:
            summary['overall_system_confidence'] = statistics.mean(confidence_scores)
        
        return summary
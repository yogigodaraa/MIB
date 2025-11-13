"""
Tension Monitoring Service
Enhanced tension monitoring with accuracy improvements.
"""

import math
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import logging

from ..models import HookData, Alert, TensionPrediction

logger = logging.getLogger(__name__)


class TensionMonitoringService:
    """Enhanced tension monitoring with accuracy improvements"""
    
    def __init__(self):
        self.sensor_data_buffer = {}  # Rolling buffer for each sensor
        self.sensor_calibration = {}  # Calibration data for each sensor
        self.environmental_data = {}  # Environmental factors affecting tension
        self.tension_baselines = {}   # Baseline tensions for each hook
        self.anomaly_detection = {}   # Anomaly detection for each sensor
        self.prediction_models = {}   # Predictive models for each hook
        
        # Configuration
        self.config = {
            'buffer_size': 50,
            'outlier_threshold': 2.5,
            'confidence_threshold': 0.7,
            'calibration_drift_limit': 5,
            'smoothing_window': 5,
            'prediction_window': 10,
            'alert_thresholds': {
                "low": 30,
                "medium": 70, 
                "high": 85,
                "critical": 95
            }
        }
        
    def process_tension_reading(self, hook_id: str, raw_tension: float, 
                               sensor_metadata: dict = None) -> dict:
        """Process raw tension reading with accuracy enhancements"""
        
        if hook_id not in self.sensor_data_buffer:
            self._initialize_sensor(hook_id)
        
        timestamp = datetime.now()
        raw_reading = {
            'value': raw_tension,
            'timestamp': timestamp,
            'metadata': sensor_metadata or {}
        }
        
        self.sensor_data_buffer[hook_id].append(raw_reading)
        
        return self._enhance_accuracy(hook_id, raw_reading)
    
    def _initialize_sensor(self, hook_id: str):
        """Initialize sensor data structures"""
        self.sensor_data_buffer[hook_id] = deque(maxlen=self.config['buffer_size'])
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
        """Apply accuracy enhancement techniques"""
        
        # Outlier detection
        is_outlier, outlier_score = self._detect_outlier(hook_id, raw_reading['value'])
        
        # Sensor drift compensation
        drift_corrected = self._compensate_drift(hook_id, raw_reading['value'])
        
        # Environmental compensation
        env_corrected = self._compensate_environmental(hook_id, drift_corrected, raw_reading['timestamp'])
        
        # Smoothing and noise reduction
        smoothed_value = self._apply_smoothing(hook_id, env_corrected)
        
        # Cross-validation with nearby sensors
        cross_validated = self._cross_validate(hook_id, smoothed_value)
        
        # Calculate confidence score
        confidence = self._calculate_confidence(hook_id, raw_reading['value'], cross_validated, is_outlier)
        
        return {
            'hook_id': hook_id,
            'raw_value': raw_reading['value'],
            'processed_value': cross_validated if confidence > self.config['confidence_threshold'] else None,
            'confidence_score': confidence,
            'is_outlier': is_outlier,
            'outlier_score': outlier_score,
            'drift_correction': drift_corrected - raw_reading['value'],
            'environmental_correction': env_corrected - drift_corrected,
            'smoothing_applied': smoothed_value - env_corrected,
            'cross_validation_delta': cross_validated - smoothed_value,
            'timestamp': raw_reading['timestamp'],
            'quality_flags': self._generate_quality_flags(hook_id, confidence, is_outlier),
            'recommendations': self._generate_accuracy_recommendations(hook_id, confidence, is_outlier)
        }
    
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
        statistical_outlier = z_score > self.config['outlier_threshold']
        
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
        
        is_outlier = statistical_outlier or iqr_outlier or rate_outlier
        outlier_score = max(z_score / self.config['outlier_threshold'], 
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
        
        time_since_calib = datetime.now() - calib_data['last_calibration']
        hours_elapsed = time_since_calib.total_seconds() / 3600
        
        drift_correction = calib_data['drift_rate'] * hours_elapsed
        corrected_value = (value + calib_data['offset'] - drift_correction) * calib_data['scale_factor']
        
        return corrected_value
    
    def _compensate_environmental(self, hook_id: str, value: float, timestamp: datetime) -> float:
        """Compensate for environmental factors"""
        env_factors = self.environmental_data.get(hook_id, {})
        
        # Temperature compensation
        temp_compensation = 0.0
        if 'temperature' in env_factors:
            temp_delta = env_factors['temperature'] - 20
            temp_compensation = value * 0.001 * temp_delta
        
        # Humidity compensation
        humidity_compensation = 0.0
        if 'humidity' in env_factors:
            humidity_delta = env_factors['humidity'] - 50
            humidity_compensation = value * 0.0005 * humidity_delta
        
        # Wind load compensation
        wind_compensation = 0.0
        if 'wind_speed' in env_factors and 'wind_direction' in env_factors:
            wind_effect = self._calculate_wind_effect(hook_id, env_factors)
            wind_compensation = wind_effect
        
        return value - temp_compensation - humidity_compensation + wind_compensation
    
    def _apply_smoothing(self, hook_id: str, value: float) -> float:
        """Apply smoothing to reduce noise"""
        buffer = self.sensor_data_buffer[hook_id]
        if len(buffer) < self.config['smoothing_window']:
            return value
        
        recent_values = []
        for reading in list(buffer)[-self.config['smoothing_window']:]:
            if not self._detect_outlier(hook_id, reading['value'])[0]:
                recent_values.append(reading['value'])
        
        if not recent_values:
            return value
        
        # Exponential weighted moving average
        alpha = 0.3
        ema = recent_values[0]
        for val in recent_values[1:]:
            ema = alpha * val + (1 - alpha) * ema
        
        # Adaptive smoothing based on rate of change
        if len(recent_values) >= 2:
            rate_of_change = abs(recent_values[-1] - recent_values[-2])
            avg_rate = statistics.mean([abs(recent_values[i] - recent_values[i-1]) 
                                      for i in range(1, len(recent_values))])
            
            if rate_of_change > avg_rate * 2:
                smoothing_factor = 0.7  # Less smoothing
            else:
                smoothing_factor = 0.3  # More smoothing
            
            smoothed_value = smoothing_factor * value + (1 - smoothing_factor) * ema
        else:
            smoothed_value = ema
        
        return smoothed_value
    
    def _cross_validate(self, hook_id: str, value: float) -> float:
        """Cross-validate with nearby sensors"""
        # Placeholder for cross-validation logic
        return value
    
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
            if std_recent < 5:
                confidence_factors.append(0.90)
            elif std_recent < 15:
                confidence_factors.append(0.75)
            else:
                confidence_factors.append(0.50)
        
        # Processing delta
        processing_delta = abs(processed_value - raw_value) / max(raw_value, 1)
        if processing_delta < 0.05:
            confidence_factors.append(0.95)
        elif processing_delta < 0.15:
            confidence_factors.append(0.80)
        else:
            confidence_factors.append(0.60)
        
        confidence = sum(confidence_factors) / len(confidence_factors)
        return min(1.0, max(0.0, confidence))
    
    def _generate_quality_flags(self, hook_id: str, confidence: float, is_outlier: bool) -> List[str]:
        """Generate quality flags for the reading"""
        flags = []
        
        if confidence < 0.5:
            flags.append("LOW_CONFIDENCE")
        
        if is_outlier:
            flags.append("OUTLIER_DETECTED")
        
        calib_data = self.sensor_calibration[hook_id]
        days_since_calib = (datetime.now() - calib_data['last_calibration']).days
        
        if days_since_calib > 90:
            flags.append("CALIBRATION_OVERDUE")
        elif days_since_calib > 30:
            flags.append("CALIBRATION_DUE_SOON")
        
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
    
    def _calculate_wind_effect(self, hook_id: str, env_factors: dict) -> float:
        """Calculate wind effect on hook tension"""
        wind_speed = env_factors.get('wind_speed', 0)
        wind_direction = env_factors.get('wind_direction', 0)
        
        wind_factor = (wind_speed / 50.0) ** 2
        directional_factor = math.cos(math.radians(wind_direction))
        
        return wind_factor * directional_factor * 10
    
    def get_alert_level(self, tension: float) -> str:
        """Get alert level based on tension value"""
        thresholds = self.config['alert_thresholds']
        
        if tension >= thresholds['critical']:
            return 'critical'
        elif tension >= thresholds['high']:
            return 'high'
        elif tension >= thresholds['medium']:
            return 'medium'
        elif tension >= thresholds['low']:
            return 'low'
        else:
            return 'safe'
    
    def predict_tension_trend(self, hook_id: str) -> TensionPrediction:
        """Predict tension trend for a hook"""
        if hook_id not in self.sensor_data_buffer or len(self.sensor_data_buffer[hook_id]) < 3:
            return TensionPrediction(trend='stable', confidence=0.5)
        
        history = list(self.sensor_data_buffer[hook_id])[-10:]
        tensions = [reading['value'] for reading in history]
        
        # Calculate simple linear trend
        n = len(tensions)
        x_sum = sum(range(n))
        y_sum = sum(tensions)
        xy_sum = sum(i * tensions[i] for i in range(n))
        x2_sum = sum(i * i for i in range(n))
        
        if n * x2_sum - x_sum * x_sum == 0:
            return TensionPrediction(trend='stable', current=tensions[-1])
        
        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
        
        # Predict tension in next 5 minutes
        future_tension = tensions[-1] + slope * 30  # 30 data points ~ 5 minutes
        
        if abs(slope) < 0.1:
            trend = 'stable'
        elif slope > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        # Calculate time to critical if increasing
        time_to_critical = None
        if slope > 0:
            critical_threshold = self.config['alert_thresholds']['critical']
            time_steps = (critical_threshold - tensions[-1]) / slope
            if time_steps > 0:
                time_to_critical = (time_steps * 10) / 60  # Convert to minutes
        
        return TensionPrediction(
            trend=trend,
            slope=slope,
            current=tensions[-1],
            predicted_5min=future_tension,
            confidence=0.7,
            time_to_critical=time_to_critical
        )
    
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
                # Get latest reading confidence
                confidence = 0.8  # Placeholder
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
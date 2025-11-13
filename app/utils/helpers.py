"""
Helper Utilities
Common utility functions used across the application.
"""

from datetime import datetime
from typing import Any


def convert_to_serializable(obj: Any) -> Any:
    """Convert datetime objects to strings for JSON serialization"""
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    else:
        return obj


def get_alert_priority(level: str) -> int:
    """Get numeric priority for alert sorting"""
    priorities = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1, 'safe': 0}
    return priorities.get(level, 0)


def categorize_hooks_by_function(berth_data: dict) -> dict:
    """Categorize hooks by their mooring function"""
    categories = {
        'bow_lines': [],      # Forward lines
        'stern_lines': [],    # Aft lines  
        'breast_lines': [],   # Side-to-side lines
        'spring_lines': [],   # Angled lines
        'unknown': []         # Unclassified
    }
    
    for bollard in berth_data.get('bollards', []):
        for hook in bollard.get('hooks', []):
            line_type = hook.get('attachedLine', '').upper()
            hook_with_location = {**hook, 'bollard': bollard['name']}
            
            if any(keyword in line_type for keyword in ['BOW', 'FORWARD', 'HEAD']):
                categories['bow_lines'].append(hook_with_location)
            elif any(keyword in line_type for keyword in ['STERN', 'AFT', 'TAIL']):
                categories['stern_lines'].append(hook_with_location)
            elif 'BREAST' in line_type:
                categories['breast_lines'].append(hook_with_location)
            elif 'SPRING' in line_type:
                categories['spring_lines'].append(hook_with_location)
            else:
                categories['unknown'].append(hook_with_location)
    
    return categories


def validate_hook_data_accuracy(berth_data: dict) -> dict:
    """Cross-validate hook tensions for accuracy"""
    import statistics
    
    hooks = []
    for bollard in berth_data.get('bollards', []):
        hooks.extend(bollard.get('hooks', []))
    
    # Check for anomalies
    tensions = [h.get('tension') for h in hooks if h.get('tension') is not None]
    if not tensions:
        return {'status': 'no_data', 'confidence': 0.0}
    
    avg_tension = sum(tensions) / len(tensions)
    std_dev = statistics.stdev(tensions) if len(tensions) > 1 else 0
    
    # Flag outliers
    outliers = []
    for hook in hooks:
        if hook.get('tension') and abs(hook['tension'] - avg_tension) > 2 * std_dev:
            outliers.append({
                'hook': hook['name'],
                'tension': hook['tension'],
                'expected_range': f"{avg_tension - std_dev:.1f}-{avg_tension + std_dev:.1f}"
            })
    
    return {
        'status': 'validated',
        'confidence': max(0.3, 1.0 - (len(outliers) / len(hooks))) if hooks else 0.0,
        'outliers': outliers,
        'average_tension': avg_tension,
        'standard_deviation': std_dev
    }


def calculate_time_to_critical(current_tension: float, slope: float, critical_threshold: float = 95) -> float:
    """Calculate estimated time until tension reaches critical level"""
    if slope <= 0:
        return None
    
    time_to_critical = (critical_threshold - current_tension) / slope
    if time_to_critical <= 0:
        return None
    
    # Convert to minutes (assuming 2-second intervals)
    minutes = (time_to_critical * 2) / 60
    return round(minutes, 1) if minutes > 0 else None
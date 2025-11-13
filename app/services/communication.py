"""
Communication Service
Service for managing crew communication, alerts, and responses.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

from ..models import (
    CrewMember, AlertResponse, CommunicationMessage, 
    Alert, ManualDataEntry
)

logger = logging.getLogger(__name__)


class CommunicationService:
    """Service for managing crew communication and alerts"""
    
    def __init__(self):
        self.crew_status: Dict[str, CrewMember] = {}
        self.communication_log: List[CommunicationMessage] = []
        self.crew_responses: Dict[str, List[AlertResponse]] = {}
        self.active_alerts: Dict[str, dict] = {}
        
        # Initialize sample crew data
        self._initialize_crew()
    
    def _initialize_crew(self):
        """Initialize sample crew data"""
        sample_crew = [
            CrewMember(
                id="crew_001",
                name="Chief Officer Johnson",
                role="deck_officer",
                phone="+61400123456",
                radio_channel="bridge",
                location="Bridge",
                status="available"
            ),
            CrewMember(
                id="crew_002",
                name="Bosun Smith",
                role="bosun",
                phone="+61400654321",
                radio_channel="deck",
                location="Foredeck",
                status="available"
            ),
            CrewMember(
                id="crew_003",
                name="AB Williams",
                role="able_seaman",
                phone="+61400789012",
                radio_channel="deck",
                location="Stern",
                status="available"
            )
        ]
        
        for crew in sample_crew:
            self.crew_status[crew.id] = crew
    
    async def send_sms_alert(self, phone_number: str, message: str, priority: str = "medium") -> str:
        """Send SMS alert to crew member"""
        message_id = f"sms_{datetime.now().timestamp()}"
        
        comm_message = CommunicationMessage(
            id=message_id,
            message_type="sms",
            recipient=phone_number,
            content=message,
            priority=priority,
            sent_at=datetime.now(),
            status="sent"
        )
        
        self.communication_log.append(comm_message)
        
        # Simulate SMS delivery delay
        await asyncio.sleep(0.1)
        
        logger.info(f"SMS sent to {phone_number}: {message}")
        return message_id
    
    async def send_push_notification(self, crew_id: str, title: str, message: str, priority: str = "medium") -> str:
        """Send push notification to crew mobile app"""
        message_id = f"push_{datetime.now().timestamp()}"
        
        comm_message = CommunicationMessage(
            id=message_id,
            message_type="push",
            recipient=crew_id,
            content=f"{title}: {message}",
            priority=priority,
            sent_at=datetime.now(),
            status="sent"
        )
        
        self.communication_log.append(comm_message)
        
        logger.info(f"Push notification sent to {crew_id}: {title}")
        return message_id
    
    async def broadcast_radio_alert(self, message: str, channel: str = "bridge") -> str:
        """Broadcast critical alert over radio system"""
        message_id = f"radio_{datetime.now().timestamp()}"
        
        comm_message = CommunicationMessage(
            id=message_id,
            message_type="radio",
            recipient=f"channel_{channel}",
            content=message,
            priority="critical",
            sent_at=datetime.now(),
            status="broadcasted"
        )
        
        self.communication_log.append(comm_message)
        
        logger.info(f"Radio broadcast on {channel}: {message}")
        return message_id
    
    def process_crew_response(self, alert_id: str, crew_id: str, response_type: str, message: str = None) -> AlertResponse:
        """Process crew response to an alert"""
        
        response = AlertResponse(
            alert_id=alert_id,
            crew_member_id=crew_id,
            response_type=response_type,
            message=message,
            timestamp=datetime.now(),
            location=self.crew_status.get(crew_id, {}).location if crew_id in self.crew_status else "unknown"
        )
        
        # Store response
        if alert_id not in self.crew_responses:
            self.crew_responses[alert_id] = []
        self.crew_responses[alert_id].append(response)
        
        # Update crew status
        if crew_id in self.crew_status:
            if response_type == "acknowledged":
                self.crew_status[crew_id].status = "responding"
            elif response_type == "resolved":
                self.crew_status[crew_id].status = "available"
        
        # Update alert status
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id]["last_response"] = response.dict()
            if response_type == "resolved":
                self.active_alerts[alert_id]["status"] = "resolved"
                self.active_alerts[alert_id]["resolved_at"] = datetime.now().isoformat()
        
        logger.info(f"Crew response recorded: {crew_id} {response_type} alert {alert_id}")
        
        return response
    
    async def trigger_alert_cascade(self, alert: Alert) -> str:
        """Trigger appropriate communication channels based on alert level"""
        
        alert_id = f"alert_{datetime.now().timestamp()}"
        
        # Store active alert
        self.active_alerts[alert_id] = {
            "id": alert_id,
            "hook_id": alert.hook_id,
            "level": alert.level,
            "tension": alert.processed_tension or alert.raw_tension,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "communications_sent": []
        }
        
        # Prepare alert messages
        location = f"{alert.berth} - {alert.hook}"
        tension = alert.processed_tension or alert.raw_tension or 0
        
        if alert.level == "critical":
            # CRITICAL: Radio + SMS + Push
            radio_msg = f"EMERGENCY: Critical tension at {location}. {tension}% load. Immediate action required."
            sms_msg = f"🚨 CRITICAL: {location} at {tension}% tension. ACT NOW!"
            push_title = "CRITICAL TENSION ALERT"
            push_msg = f"{location}: {tension}% load - Immediate action required"
            
            # Send all communication types
            radio_id = await self.broadcast_radio_alert(radio_msg, "emergency")
            
            # Send to all available crew
            for crew_id, crew_info in self.crew_status.items():
                if crew_info.status != "off_duty":
                    sms_id = await self.send_sms_alert(crew_info.phone or "", sms_msg, "critical")
                    push_id = await self.send_push_notification(crew_id, push_title, push_msg, "critical")
                    
                    self.active_alerts[alert_id]["communications_sent"].extend([radio_id, sms_id, push_id])
        
        elif alert.level == "high":
            # HIGH: SMS + Push to relevant crew
            sms_msg = f"⚠️ HIGH tension alert: {location} at {tension}% load. Monitor and prepare for adjustment."
            push_title = "High Tension Alert"
            push_msg = f"{location}: {tension}% - Monitor closely"
            
            # Send to deck officers and bosun
            for crew_id, crew_info in self.crew_status.items():
                if crew_info.role in ["deck_officer", "bosun"] and crew_info.status != "off_duty":
                    sms_id = await self.send_sms_alert(crew_info.phone or "", sms_msg, "high")
                    push_id = await self.send_push_notification(crew_id, push_title, push_msg, "high")
                    
                    self.active_alerts[alert_id]["communications_sent"].extend([sms_id, push_id])
        
        elif alert.level == "medium":
            # MEDIUM: Push notifications only
            push_title = "Tension Warning"
            push_msg = f"{location}: {tension}% tension - Attention required"
            
            # Send to available crew
            for crew_id, crew_info in self.crew_status.items():
                if crew_info.status == "available":
                    push_id = await self.send_push_notification(crew_id, push_title, push_msg, "medium")
                    self.active_alerts[alert_id]["communications_sent"].append(push_id)
        
        return alert_id
    
    def get_crew_status_summary(self) -> dict:
        """Get summary of all crew member statuses"""
        summary = {
            "total_crew": len(self.crew_status),
            "available": 0,
            "responding": 0,
            "busy": 0,
            "off_duty": 0,
            "crew_details": []
        }
        
        for crew_id, crew_info in self.crew_status.items():
            status = crew_info.status
            summary[status] = summary.get(status, 0) + 1
            
            # Get latest activity
            latest_response = None
            for alert_responses in self.crew_responses.values():
                for response in alert_responses:
                    if response.crew_member_id == crew_id:
                        if not latest_response or response.timestamp > latest_response.timestamp:
                            latest_response = response
            
            crew_detail = {
                "id": crew_id,
                "name": crew_info.name,
                "role": crew_info.role,
                "status": status,
                "location": crew_info.location,
                "latest_activity": latest_response.timestamp.isoformat() if latest_response else "No recent activity"
            }
            summary["crew_details"].append(crew_detail)
        
        return summary
    
    def record_manual_data_entry(self, hook_id: str, tension_value: int, crew_id: str, reason: str) -> ManualDataEntry:
        """Record manual tension data entry"""
        
        entry = ManualDataEntry(
            hook_id=hook_id,
            tension_value=tension_value,
            entered_by=crew_id,
            reason=reason,
            timestamp=datetime.now(),
            confidence=0.8
        )
        
        # Log the manual entry
        self.communication_log.append(CommunicationMessage(
            id=f"manual_{datetime.now().timestamp()}",
            message_type="manual",
            recipient="system",
            content=f"Manual data entry: {hook_id} = {tension_value}% (Reason: {reason})",
            priority="medium",
            sent_at=datetime.now(),
            status="recorded"
        ))
        
        logger.info(f"Manual data entry: {hook_id} = {tension_value}% by {crew_id}")
        
        return entry
    
    async def broadcast_custom_alert(self, message: str, priority: str = "medium", channels: List[str] = None) -> List[str]:
        """Broadcast custom alert message to crew"""
        
        if channels is None:
            channels = ["sms", "push"]
        
        message_ids = []
        
        if "radio" in channels and priority == "critical":
            radio_id = await self.broadcast_radio_alert(message, "all")
            message_ids.append(radio_id)
        
        if "sms" in channels:
            for crew_id, crew_info in self.crew_status.items():
                if crew_info.status != "off_duty" and crew_info.phone:
                    sms_id = await self.send_sms_alert(crew_info.phone, f"📢 BROADCAST: {message}", priority)
                    message_ids.append(sms_id)
        
        if "push" in channels:
            for crew_id, crew_info in self.crew_status.items():
                if crew_info.status != "off_duty":
                    push_id = await self.send_push_notification(crew_id, "Broadcast Alert", message, priority)
                    message_ids.append(push_id)
        
        return message_ids
    
    def get_communication_log(self, limit: int = 50) -> List[CommunicationMessage]:
        """Get recent communication log"""
        return self.communication_log[-limit:]
    
    def get_active_alerts(self) -> Dict[str, dict]:
        """Get all active alerts"""
        return {k: v for k, v in self.active_alerts.items() if v.get("status") == "active"}
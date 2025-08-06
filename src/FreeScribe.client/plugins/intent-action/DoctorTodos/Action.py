"""
Action handlers for doctor todo/task recognition.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Dict, Any, List
from services.intent_actions.actions.base import BaseAction, ActionResult

logger = logging.getLogger(__name__)

@dataclass
class TodoTask:
    """Represents a doctor todo task."""
    task_type: str
    description: str
    priority: str = "medium"
    due_date: str = None
    patient_id: str = None
    status: str = "pending"

class PrescribeMedicationAction(BaseAction):
    """Action for handling medication prescription tasks."""
    
    def __init__(self):
        """Initialize the prescription action."""
        super().__init__()
    
    @property
    def action_id(self) -> str:
        """Get the unique identifier for this action."""
        return "prescribe_medication"

    @property
    def display_name(self) -> str:
        """Get the human-readable name for this action."""
        return "Prescribe Medication"

    @property
    def description(self) -> str:
        """Get the detailed description of what this action does."""
        return "Create a prescription task for a medication"

    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if this action can handle the given intent.
        
        :param intent_name: Name of the intent to check
        :param metadata: Intent metadata containing parameters
        :return: True if this action can handle the intent
        """
        return intent_name == "prescribe_medication"

    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """
        Execute the action for the given intent.
        
        :param intent_name: Name of the intent to execute
        :param metadata: Intent metadata containing parameters
        :return: Result of the action execution
        """
        try:
            # Extract entities from parameters instead of directly from metadata
            parameters = metadata.get("parameters", {})
            entities = parameters.get("entities", {})
            medication = entities.get("MEDICATION", ["unknown medication"])[0] if entities.get("MEDICATION") else "unknown medication"
            task = TodoTask(
                task_type="prescription",
                description=f"Prescribe {medication}",
                priority="high"
            )
            
            logger.info(f"Created prescription task: {task.description}")
            
            return ActionResult(
                success=True,
                message=f"Added prescription task: {medication}",
                data={
                    "task": asdict(task),
                    "action_type": "prescribe_medication",
                    "medication": medication,
                    "title": f"Prescribe {medication}",
                    "type": "prescription_task",
                    "has_action": False,
                    "auto_complete": True
                }
            )
        except Exception as e:
            logger.error(f"Error in prescription action: {e}")
            return ActionResult(
                success=False,
                message="Failed to create prescription task",
                data={"error": str(e)}
            )

    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI configuration for displaying results."""
        return {
            "icon": "💊",
            "color": "#FF5722"
        }

    def complete_action(self, result_data: Dict[str, Any]) -> bool:
        """
        Mark the prescription action as completed.
        
        :param result_data: Data returned from the action execution
        :return: True if the action was successfully marked as completed
        """
        try:
            task_data = result_data.get("task", {})
            logger.info(f"Completed prescription task: {task_data.get('description', 'Unknown task')}")
            return True
        except Exception as e:
            logger.error(f"Error completing prescription action: {e}")
            return False

class ScheduleTaskAction(BaseAction):
    """Action for handling scheduling tasks."""
    
    def __init__(self):
        """Initialize the scheduling action."""
        super().__init__()
    
    @property
    def action_id(self) -> str:
        """Get the unique identifier for this action."""
        return "schedule_task"

    @property
    def display_name(self) -> str:
        """Get the human-readable name for this action."""
        return "Schedule Task"

    @property
    def description(self) -> str:
        """Get the detailed description of what this action does."""
        return "Create a scheduling task for appointments, referrals, or tests"

    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if this action can handle the given intent.
        
        :param intent_name: Name of the intent to check
        :param metadata: Intent metadata containing parameters
        :return: True if this action can handle the intent
        """
        return intent_name == "schedule_task"

    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """
        Execute the action for the given intent.
        
        :param intent_name: Name of the intent to execute
        :param metadata: Intent metadata containing parameters
        :return: Result of the action execution
        """
        try:
            # Extract entities from parameters instead of directly from metadata
            parameters = metadata.get("parameters", {})
            entities = parameters.get("entities", {})
            specialist = entities.get("SPECIALIST", [""])[0] if entities.get("SPECIALIST") else ""
            diagnostic_test = entities.get("DIAGNOSTIC_TEST", [""])[0] if entities.get("DIAGNOSTIC_TEST") else ""
            lab_test = entities.get("LAB_TEST", [""])[0] if entities.get("LAB_TEST") else ""
            
            if specialist:
                description = f"Refer to {specialist}"
                task_subtype = "referral"
                icon = "👨‍⚕️"
            elif diagnostic_test:
                description = f"Schedule {diagnostic_test}"
                task_subtype = "diagnostic"
                icon = "🔬"
            elif lab_test:
                description = f"Order {lab_test}"
                task_subtype = "lab_order"
                icon = "🧪"
            else:
                description = f"Schedule follow-up appointment"
                task_subtype = "appointment"
                icon = "📅"
            
            task = TodoTask(
                task_type="scheduling",
                description=description,
                priority="medium"
            )
            
            logger.info(f"Created scheduling task: {task.description}")
            
            return ActionResult(
                success=True,
                message=f"Added scheduling task: {description}",
                data={
                    "task": asdict(task),
                    "action_type": "schedule_task",
                    "task_subtype": task_subtype,
                    "title": description,
                    "type": "scheduling_task",
                    "icon": icon,
                    "has_action": False,
                    "auto_complete": True
                }
            )
        except Exception as e:
            logger.error(f"Error in scheduling action: {e}")
            return ActionResult(
                success=False,
                message="Failed to create scheduling task",
                data={"error": str(e)}
            )

    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI configuration for displaying results."""
        return {
            "icon": "📅",
            "color": "#4CAF50"
        }

    def complete_action(self, result_data: Dict[str, Any]) -> bool:
        """
        Mark the scheduling action as completed.
        
        :param result_data: Data returned from the action execution
        :return: True if the action was successfully marked as completed
        """
        try:
            task_data = result_data.get("task", {})
            logger.info(f"Completed scheduling task: {task_data.get('description', 'Unknown task')}")
            return True
        except Exception as e:
            logger.error(f"Error completing scheduling action: {e}")
            return False

class DocumentMedicalAction(BaseAction):
    """Action for handling medical documentation tasks."""
    
    def __init__(self):
        """Initialize the documentation action."""
        super().__init__()
    
    @property
    def action_id(self) -> str:
        """Get the unique identifier for this action."""
        return "document_medical"

    @property
    def display_name(self) -> str:
        """Get the human-readable name for this action."""
        return "Document Medical"

    @property
    def description(self) -> str:
        """Get the detailed description of what this action does."""
        return "Create a medical documentation task"

    def can_handle_intent(self, intent_name: str, metadata: Dict[str, Any]) -> bool:
        """
        Check if this action can handle the given intent.
        
        :param intent_name: Name of the intent to check
        :param metadata: Intent metadata containing parameters
        :return: True if this action can handle the intent
        """
        return intent_name == "document_medical"

    def execute(self, intent_name: str, metadata: Dict[str, Any]) -> ActionResult:
        """
        Execute the action for the given intent.
        
        :param intent_name: Name of the intent to execute
        :param metadata: Intent metadata containing parameters
        :return: Result of the action execution
        """
        try:
            # Extract entities from parameters instead of directly from metadata
            parameters = metadata.get("parameters", {})
            entities = parameters.get("entities", {})
            medical_record = entities.get("MEDICAL_RECORD", ["medical record"])[0] if entities.get("MEDICAL_RECORD") else "medical record"
            vital_sign = entities.get("VITAL_SIGN", [""])[0] if entities.get("VITAL_SIGN") else ""
            symptom = entities.get("SYMPTOM", [""])[0] if entities.get("SYMPTOM") else ""
            
            if vital_sign:
                description = f"Record {vital_sign}"
                doc_type = "vital_signs"
            elif symptom:
                description = f"Document {symptom}"
                doc_type = "symptoms"
            else:
                description = f"Update {medical_record}"
                doc_type = "medical_record"
            
            task = TodoTask(
                task_type="documentation",
                description=description,
                priority="low"
            )
            
            logger.info(f"Created documentation task: {task.description}")
            
            return ActionResult(
                success=True,
                message=f"Added documentation task: {description}",
                data={
                    "task": asdict(task),
                    "action_type": "document_medical",
                    "doc_type": doc_type,
                    "title": description,
                    "type": "documentation_task",
                    "has_action": False,
                    "auto_complete": True
                }
            )
        except Exception as e:
            logger.error(f"Error in documentation action: {e}")
            return ActionResult(
                success=False,
                message="Failed to create documentation task",
                data={"error": str(e)}
            )

    def get_ui_data(self) -> Dict[str, Any]:
        """Get UI configuration for displaying results."""
        return {
            "icon": "📋",
            "color": "#9C27B0"
        }

    def complete_action(self, result_data: Dict[str, Any]) -> bool:
        """
        Mark the documentation action as completed.
        
        :param result_data: Data returned from the action execution
        :return: True if the action was successfully marked as completed
        """
        try:
            task_data = result_data.get("task", {})
            logger.info(f"Completed documentation task: {task_data.get('description', 'Unknown task')}")
            return True
        except Exception as e:
            logger.error(f"Error completing documentation action: {e}")
            return False

# Export actions for registration
exported_actions = [
    PrescribeMedicationAction,
    ScheduleTaskAction,
    DocumentMedicalAction
]
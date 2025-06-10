"""
Intent action manager for coordinating intent recognition and action execution.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .intents import SpacyIntentRecognizer, Intent
from .actions import BaseAction, PrintMapAction, ShowDirectionsAction
from .plugin_manager import discover_action_plugin_files, load_actions_from_files, get_plugins_dir, INTENT_ACTION_DIR


logger = logging.getLogger(__name__)

class IntentActionManager:
    """
    Manages intent recognition and action execution.
    
    This class coordinates between intent recognizers and action handlers,
    providing a unified interface for processing transcribed text.
    """
    
    def __init__(self, maps_directory: Path, google_maps_api_key: Optional[str] = None):
        """
        Initialize the intent action manager.
        
        :param maps_directory: Directory to store map images
        :param google_maps_api_key: Optional Google Maps API key. If not provided, will try to get from settings.
        """
        self.maps_directory = maps_directory
        
        # Initialize recognizer
        self.intent_recognizer = SpacyIntentRecognizer()
        self.intent_recognizer.initialize()
        
        # Register actions
        self.actions: List[BaseAction] = [
            PrintMapAction(maps_directory, google_maps_api_key),
            ShowDirectionsAction()
        ]

        plugin_file_list = discover_action_plugin_files(get_plugins_dir(INTENT_ACTION_DIR))

        plugin_classes = load_actions_from_files(plugin_file_list)

        # Register plugin actions
        for action_cls in plugin_classes:
            try:
                self.actions.append(action_cls)
                logger.info(f"Registered plugin action: {action_cls.action_id}")
            except Exception as e:
                logger.error(f"Failed to instantiate action {action_cls}: {e}")
        
        # Register action handlers
        for action in self.actions:
            logger.info(f"Registered action handler: {action.action_id}")
        
    def process_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Process transcribed text to recognize intents and execute actions.
        
        :param text: Transcribed text to process
        :return: List of action results with UI data
        """
        logger.debug(f"Processing text: {text}")
        results = []
        
        # Recognize intents
        intents = self.intent_recognizer.recognize_intent(text)
        logger.debug(f"Intents: {intents}")
        # Process each intent
        for intent in intents:
            # Find all matching actions
            matching_actions = self._find_actions_for_intent(intent)
            if not matching_actions:
                logger.debug(f"No actions found for intent: {intent}")
                continue
                
            # Execute each matching action
            for action in matching_actions:
                logger.debug(f"Executing action {action.action_id} for intent: {intent}")
                result = action.execute(intent.name, intent.metadata)
                logger.debug(f"Result from {action.action_id}: {result}")
                if result.success:
                    # Add UI data
                    ui_data = action.get_ui_data()
                    logger.info(f"FULL FATA: {result}")
                    results.append({
                        "action_id": action.action_id,
                        "display_name": action.display_name,
                        "message": result.message,
                        "data": result.data,
                        "ui": ui_data
                    })
                
        return results
        
    def _find_actions_for_intent(self, intent: Intent) -> List[BaseAction]:
        """
        Find all action handlers that can handle the given intent.
        
        :param intent: Intent to find handlers for
        :return: List of matching action handlers
        """
        return [
            action
            for action in self.actions
            if action.can_handle_intent(intent.name, intent.metadata)
        ]
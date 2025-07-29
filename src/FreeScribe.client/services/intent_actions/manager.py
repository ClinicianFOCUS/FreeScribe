"""
Intent action manager for coordinating intent recognition and action execution.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .intents import SpacyIntentRecognizer, Intent
from .actions import BaseAction, PrintMapAction, ShowDirectionsAction
from .plugin_manager import load_plugin_actions, get_plugins_dir, INTENT_ACTION_DIR


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
        self.google_maps_api_key = google_maps_api_key
        
        # Initialize recognizer but don't load plugins yet
        self.intent_recognizer = SpacyIntentRecognizer()
        
        # Initialize basic actions
        self.actions: List[BaseAction] = []
        
        # Defer initialization to a separate method
        self.initialize()
    
    def initialize(self):
        """Initialize the recognizer and load all actions."""
        # Initialize recognizer (this will load plugin patterns)
        self.intent_recognizer.initialize()
        
        # Register built-in actions
        self.actions = [
            PrintMapAction(self.maps_directory, self.google_maps_api_key),
            ShowDirectionsAction()
        ]

        # Load plugin actions
        plugin_actions = load_plugin_actions(get_plugins_dir(INTENT_ACTION_DIR))
        self.actions.extend(plugin_actions)
        
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
                    logger.info(f"FULL DATA: {result}")
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
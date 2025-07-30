"""
Intent action manager for coordinating intent recognition and action execution.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .intents import SpacyIntentRecognizer, Intent
from .actions import BaseAction
from .plugin_manager import load_plugin_actions, get_plugins_dir, INTENT_ACTION_DIR

from .actions import BaseAction, PrintMapAction, ShowDirectionsAction
from .plugin_manager import (
    load_plugin_actions, 
    get_plugins_dir, 
    INTENT_ACTION_DIR,
    get_plugin_state,
    load_specific_plugin,
    unload_plugin,
    reload_plugin,
    get_loaded_plugins_info,
    get_plugin_details_for_ui,
    get_all_plugins_for_ui
)

logger = logging.getLogger(__name__)

class IntentActionManager:
    """
    Manages intent recognition and action execution.
    
    This class coordinates between intent recognizers and action handlers,
    providing a unified interface for processing transcribed text.
    """
    
    def __init__(self):
        """
        Initialize the intent action manager.
        
        """
        
        # Initialize recognizer but don't load plugins yet
        self.intent_recognizer = SpacyIntentRecognizer()
        
        # Initialize built-in actions (separate from plugin actions)
        self.builtin_actions: List[BaseAction] = [
            PrintMapAction(self.maps_directory, self.google_maps_api_key),
            ShowDirectionsAction()
        ]
        
        # Defer initialization to a separate method
        self.initialize()
    
    def initialize(self):
        """Initialize the recognizer and load all actions."""
        # Initialize recognizer (this will load plugin patterns)
        self.intent_recognizer.initialize()
        
        # Register built-in actions
        self.actions = [
        ]

        # Load plugin actions
        load_plugin_actions(get_plugins_dir(INTENT_ACTION_DIR))
        
        # Register action handlers
        for action in self.get_all_actions():
            logger.info(f"Registered action handler: {action.action_id}")
    
    def get_all_actions(self) -> List[BaseAction]:
        """Get all actions (built-in + plugin actions)."""
        plugin_state = get_plugin_state()
        plugin_actions = plugin_state.get_all_actions()
        return self.builtin_actions + plugin_actions
    
    def reload_plugins(self):
        """Reload all plugins."""
        logger.info("Reloading all plugins...")
        
        # Reload plugins (this clears and reloads all)
        load_plugin_actions(get_plugins_dir(INTENT_ACTION_DIR))
        
        # Reinitialize recognizer with new patterns
        self.intent_recognizer.initialize()
        
        total_actions = len(self.get_all_actions())
        logger.info(f"Reloaded plugins. Total actions: {total_actions}")
    
    def add_plugin(self, plugin_name: str) -> bool:
        """
        Add a specific plugin to the manager.
        
        :param plugin_name: Name of the plugin folder
        :return: True if successfully added, False otherwise
        """
        try:
            result = load_specific_plugin(plugin_name)
            
            if result.get("actions"):
                logger.info(f"Added {len(result['actions'])} actions from plugin {result['name']}")
            
            # Reinitialize recognizer to include new patterns
            if result.get("intent_patterns") or result.get("entity_patterns"):
                self.intent_recognizer.initialize()
                logger.info(f"Reinitialized recognizer with new patterns from {result['name']}")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Failed to add plugin {plugin_name}: {e}")
            return False
    
    def remove_plugin(self, plugin_name: str) -> bool:
        """
        Remove a specific plugin from the manager.
        
        :param plugin_name: Name of the plugin to remove
        :return: True if successfully removed, False otherwise
        """
        try:
            plugin_state = get_plugin_state()
            
            if not plugin_state.is_plugin_loaded(plugin_name):
                logger.warning(f"Plugin {plugin_name} is not loaded")
                return False
            
            # Unload the plugin (this returns the removed plugin data)
            removed_plugin = unload_plugin(plugin_name)
            
            if removed_plugin:
                logger.info(f"Removed plugin {plugin_name} with {len(removed_plugin.get('actions', []))} actions")
                # Reinitialize recognizer to remove patterns
                self.intent_recognizer.initialize()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: str) -> bool:
        """
        Reload a specific plugin.
        
        :param plugin_name: Name of the plugin to reload
        :return: True if successfully reloaded, False otherwise
        """
        try:
            result = reload_plugin(plugin_name)
            
            if result:
                logger.info(f"Reloaded plugin {plugin_name}")
                # Reinitialize recognizer
                self.intent_recognizer.initialize()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about loaded plugins."""
        return get_loaded_plugins_info()
    
    def get_plugin_details(self, plugin_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plugin for UI."""
        return get_plugin_details_for_ui(plugin_name)
    
    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        """Get information about all plugins for UI."""
        return get_all_plugins_for_ui()
        
    def process_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Process transcribed text to recognize intents and execute actions.
        
        :param text: Transcribed text to process
        :return: List of action results with UI data
        """
        logger.debug(f"Processing text: {text}")
        results = []
        
        # Get all current actions
        all_actions = self.get_all_actions()
        
        # Recognize intents
        intents = self.intent_recognizer.recognize_intent(text)
        logger.debug(f"Intents: {intents}")
        
        # Process each intent
        for intent in intents:
            # Find all matching actions
            matching_actions = self._find_actions_for_intent(intent, all_actions)
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
                    results.append({
                        "action_id": action.action_id,
                        "display_name": action.display_name,
                        "message": result.message,
                        "data": result.data,
                        "ui": ui_data
                    })
                
        return results
        
    def _find_actions_for_intent(self, intent: Intent, actions: List[BaseAction]) -> List[BaseAction]:
        """
        Find all action handlers that can handle the given intent.
        
        :param intent: Intent to find handlers for
        :param actions: List of actions to search through
        :return: List of matching action handlers
        """
        return [
            action
            for action in actions
            if action.can_handle_intent(intent.name, intent.metadata)
        ]
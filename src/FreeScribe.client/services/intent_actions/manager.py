"""
Intent action manager for coordinating intent recognition and action execution.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .intents import SpacyIntentRecognizer, Intent
from .actions import BaseAction
from .plugin_manager import (
    get_plugins_dir, 
    INTENT_ACTION_DIR,
    PluginService
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
        
        # Initialize plugin service
        self.plugin_svc = PluginService(Path(get_plugins_dir(INTENT_ACTION_DIR)))
        
        # Initialize recognizer but don't load plugins yet
        self.intent_recognizer = SpacyIntentRecognizer()
        
        # Initialize built-in actions (separate from plugin actions)
        self.builtin_actions: List[BaseAction] = [
        ]
        
        # Defer initialization to a separate method
        self.initialize()
    
    def initialize(self):
        """Initialize the recognizer and load all actions."""
        logger.info("IntentActionManager: Starting initialization...")
        
        # Load all plugins first
        logger.info("IntentActionManager: Loading all plugins...")
        self.plugin_svc.load_all()
        
        plugin_info = self.plugin_svc.get_info()
        logger.info(f"IntentActionManager: Loaded {plugin_info.get('total_plugins', 0)} plugins")
        
        self._reinit_recognizer()
        self.actions = self.builtin_actions + self.plugin_svc.get_all_actions()
        for a in self.actions:
            logger.info(f"Registered action handler: {getattr(a, 'action_id', a.__class__.__name__)}")
        
        logger.info("IntentActionManager: Initialization complete")

    def _reinit_recognizer(self):
        """Reinitialize the intent recognizer."""
        self.intent_recognizer = SpacyIntentRecognizer()
        self.intent_recognizer.initialize()
    
    def get_all_actions(self) -> List[BaseAction]:
        """Get all actions (built-in + plugin actions)."""
        return self.builtin_actions + self.plugin_svc.get_all_actions()
    
    def remove_plugin(self, plugin_name: str) -> bool:
        """
        Remove a specific plugin from the manager.
        
        :param plugin_name: Name of the plugin to remove
        :return: True if successfully removed, False otherwise
        """
        try:
            removed = self.plugin_svc.unload(plugin_name)
            if removed:
                self._reinit_recognizer()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove plugin {plugin_name}: {e}")
            return False
    
    def reload_plugin(self, plugin_name: Optional[str] = None) -> bool:
        """
        Reload a specific plugin or all plugins if name is None.
        
        :param plugin_name: Name of the plugin to reload, or None for all
        :return: True if successfully reloaded, False otherwise
        """
        try:
            ok = self.plugin_svc.reload(plugin_name)
            if ok:
                self._reinit_recognizer()
            return ok
        except Exception as e:
            logger.error(f"Failed to reload plugin {plugin_name}: {e}")
            return False
    
    def reload_plugins(self):
        """Reload all plugins."""
        logger.info("Reloading all plugins...")        
        ok = self.plugin_svc.reload()
        if ok:
            self._reinit_recognizer()
        total_actions = len(self.get_all_actions())
        logger.info(f"Reloaded plugins. Total actions: {total_actions}")
    
    def add_plugin(self, plugin_name: str) -> bool:
        """
        Add a specific plugin to the manager.
        
        :param plugin_name: Name of the plugin folder
        :return: True if successfully added, False otherwise
        """
        try:
            result = self.plugin_svc.load(plugin_name)
            if result:
                self._reinit_recognizer()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to add plugin {plugin_name}: {e}")
            return False
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about loaded plugins."""
        return self.plugin_svc.get_info()
    
    def get_plugin_details(self, plugin_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plugin for UI."""
        return self.plugin_svc.get_details(plugin_name)
    
    def get_all_plugins_info(self) -> List[Dict[str, Any]]:
        """Get information about all plugins for UI."""
        return self.plugin_svc.list_for_ui()
        
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
                    results.append({
                        "action_id": action.action_id,
                        "display_name": action.display_name,
                        "message": result.message,
                        "data": result.data,
                        "ui": ui_data
                    })
                
        return results
        
    def _find_actions_for_intent(
        self, intent: Intent, actions: Optional[List[BaseAction]] = None
    ) -> List[BaseAction]:
        """
        Find all action handlers that can handle the given intent.
        
        :param intent: Intent to find handlers for
        :param actions: List of actions to search through, or None to use all actions
        :return: List of matching action handlers
        """
        pool = actions if actions is not None else self.get_all_actions()
        return [
            a for a in pool
            if a.can_handle_intent(intent.name, intent.metadata)
        ]
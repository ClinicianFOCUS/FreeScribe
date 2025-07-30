import os
import threading
from pathlib import Path
from utils.log_config import logger
import importlib.util
from utils.file_utils import get_resource_path
from typing import List, Tuple, Optional, TypeVar, Any, Dict

T = TypeVar("T")

INTENT_ACTION_DIR = "intent-action"

class PluginState:
    """Manages the state of loaded plugins."""
    
    def __init__(self):
        self._loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def add_module(self, module_name: str, module: Any) -> None:
        """Add a module to the tracking (for cleanup purposes)."""
        with self._lock:
            # Extract plugin name from module_name (format: plugin_name_file_stem)
            parts = module_name.split('_')
            if len(parts) >= 2:
                plugin_name = '_'.join(parts[:-1])
                if plugin_name in self._loaded_plugins:
                    if "modules" not in self._loaded_plugins[plugin_name]:
                        self._loaded_plugins[plugin_name]["modules"] = {}
                    self._loaded_plugins[plugin_name]["modules"][module_name] = module
    
    def add_plugin(self, plugin_name: str, actions: List[Any], intent_patterns: List[Any], entity_patterns: List[Any], modules: Dict[str, Any]) -> None:
        """Add a complete plugin to the loaded state."""
        with self._lock:
            import datetime
            self._loaded_plugins[plugin_name] = {
                "actions": actions,
                "intent_patterns": intent_patterns,
                "entity_patterns": entity_patterns,
                "modules": modules,
                "loaded_at": datetime.datetime.now()
            }
    
    def remove_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Remove a plugin from the loaded state and return its data."""
        with self._lock:
            if plugin_name in self._loaded_plugins:
                removed_plugin = self._loaded_plugins.pop(plugin_name)
                logger.info(f"Removed plugin {plugin_name} with {len(removed_plugin['actions'])} actions, "
                           f"{len(removed_plugin['intent_patterns'])} intent patterns, "
                           f"{len(removed_plugin['entity_patterns'])} entity patterns")
                return removed_plugin
            return {}
    
    def get_plugin_actions(self, plugin_name: str) -> List[Any]:
        """Get actions for a specific plugin."""
        with self._lock:
            if plugin_name in self._loaded_plugins:
                return self._loaded_plugins[plugin_name]["actions"]
            return []
    
    def get_all_actions(self) -> List[Any]:
        """Get all loaded action instances."""
        with self._lock:
            all_actions = []
            for plugin_data in self._loaded_plugins.values():
                all_actions.extend(plugin_data["actions"])
            return all_actions
    
    def get_all_intent_patterns(self) -> List[Any]:
        """Get all loaded intent patterns."""
        with self._lock:
            all_patterns = []
            for plugin_data in self._loaded_plugins.values():
                all_patterns.extend(plugin_data["intent_patterns"])
            return all_patterns
    
    def get_all_entity_patterns(self) -> List[Any]:
        """Get all loaded entity patterns."""
        with self._lock:
            all_patterns = []
            for plugin_data in self._loaded_plugins.values():
                all_patterns.extend(plugin_data["entity_patterns"])
            return all_patterns
    
    def get_loaded_plugin_names(self) -> List[str]:
        """Get names of all loaded plugins."""
        with self._lock:
            return list(self._loaded_plugins.keys())
    
    def is_plugin_loaded(self, plugin_name: str) -> bool:
        """Check if a plugin is currently loaded."""
        with self._lock:
            return plugin_name in self._loaded_plugins
    
    def get_plugin_info(self, plugin_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plugin."""
        with self._lock:
            if plugin_name in self._loaded_plugins:
                plugin_data = self._loaded_plugins[plugin_name]
                return {
                    "name": plugin_name,
                    "actions": plugin_data["actions"],
                    "intent_patterns": plugin_data["intent_patterns"],
                    "entity_patterns": plugin_data["entity_patterns"],
                    "loaded_at": plugin_data["loaded_at"],
                    "action_count": len(plugin_data["actions"]),
                    "intent_count": len(plugin_data["intent_patterns"]),
                    "entity_count": len(plugin_data["entity_patterns"])
                }
            return {}
    
    def clear_all(self) -> None:
        """Clear all loaded plugins."""
        with self._lock:
            self._loaded_plugins.clear()
            logger.info("Cleared all plugin state")

# Global plugin state instance
_plugin_state = PluginState()

def get_plugin_state() -> PluginState:
    """Get the global plugin state instance."""
    return _plugin_state

def load_exported_from_files(
    base_dir: Path, 
    file_pattern: str,
    export_name: str,
    plugin_name: Optional[str] = None,
    recursive: bool = False
) -> List[T]:
    """
    Load `export_name` from all files matching `file_pattern` under `base_dir`.
    Returns a flat list of whatever was in `module.<export_name>`.
    
    :param plugin_name: Optional plugin name for state tracking
    :param recursive: If True, search recursively; if False, only direct children
    """
    results: List[T] = []
    
    # Choose search method based on recursive flag
    files = base_dir.rglob(file_pattern) if recursive else base_dir.glob(file_pattern)
    
    for file in files:
        try:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            if spec is None or spec.loader is None:
                logger.error(f"Could not create module spec for {file}")
                continue
                
            module = importlib.util.module_from_spec(spec)
            if module is None:
                logger.error(f"Could not create module from spec for {file}")
                continue
                
            spec.loader.exec_module(module)
            exported_items = getattr(module, export_name, [])
            results.extend(exported_items)
            
            # Track the module in plugin state if plugin_name is provided
            if plugin_name:
                _plugin_state.add_module(f"{plugin_name}_{file.stem}", module)
            
            logger.debug(f"Loaded {export_name} from {file}")
        except Exception as e:
            logger.error(f"Failed to load {export_name} from {file}: {e}")
    return results

def get_plugins_dir(subdir: Optional[str] = None) -> str:
    """
    Get the path to the plugins directory.
    """
    plugin_path = "plugins"

    if subdir:
        plugin_path = plugin_path + os.sep + subdir
    
    return get_resource_path(plugin_path)

def load_plugin_intent_patterns(plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR), track_state: bool = True) -> Tuple[List, List]:
    """
    Load all intent patterns and entity patterns from plugin folders.
    Each folder in plugins_dir is treated as a separate plugin.
    
    Returns a tuple of (intent_patterns, entity_patterns)
    
    :param track_state: Whether to track loaded plugins in the global state
    """
    if not os.path.exists(plugins_dir):
        logger.warning(f"Plugins directory does not exist: {plugins_dir}")
        return [], []
    
    plugins_root = Path(plugins_dir)
    all_intent_patterns = []
    all_entity_patterns = []
    
    # Iterate through each plugin folder
    for plugin_folder in plugins_root.iterdir():
        if not plugin_folder.is_dir():
            continue
            
        plugin_name = plugin_folder.name
        logger.debug(f"Loading patterns from plugin: {plugin_name}")
        
        # Load intent patterns from this specific plugin folder
        intent_patterns = load_exported_from_files(
            plugin_folder, 
            "Intent.py", 
            "exported_patterns",
            plugin_name=f"{plugin_name}_intents" if track_state else None,
            recursive=False
        )
        
        # Load entity patterns from this specific plugin folder
        entity_patterns = load_exported_from_files(
            plugin_folder, 
            "Intent.py", 
            "exported_entities",
            plugin_name=f"{plugin_name}_entities" if track_state else None,
            recursive=False
        )
        
        all_intent_patterns.extend(intent_patterns)
        all_entity_patterns.extend(entity_patterns)
        
        if intent_patterns or entity_patterns:
            logger.info(f"Loaded {len(intent_patterns)} intent patterns and {len(entity_patterns)} entity patterns from plugin: {plugin_name}")
    
    logger.info(f"Loaded {len(all_intent_patterns)} total intent patterns and {len(all_entity_patterns)} total entity patterns from plugin folders")
    return all_intent_patterns, all_entity_patterns

def load_specific_plugin(plugin_name: str, plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR), track_state: bool = True) -> Dict[str, Any]:
    """
    Load a specific plugin by name.
    
    :param plugin_name: Name of the plugin folder
    :param plugins_dir: Base plugins directory
    :param track_state: Whether to track the loaded plugin
    :return: Dictionary with loaded components
    """
    plugin_path = Path(plugins_dir) / plugin_name
    
    if not plugin_path.exists() or not plugin_path.is_dir():
        logger.error(f"Plugin directory does not exist: {plugin_path}")
        return {}
    
    logger.info(f"Loading plugin: {plugin_name}")
    
    result = {
        "name": plugin_name,
        "actions": [],
        "intent_patterns": [],
        "entity_patterns": [],
        "modules": {}
    }
    
    try:
        # Load actions from this plugin folder
        action_classes = load_exported_from_files(
            plugin_path, 
            "*Action.py", 
            "exported_actions",
            plugin_name=plugin_name if track_state else None,
            recursive=False
        )
        
        for cls in action_classes:
            try:
                action_instance = cls()
                result["actions"].append(action_instance)
            except Exception as e:
                logger.error(f"Failed to instantiate action {cls} from {plugin_name}: {e}")
        
        # Load intent patterns from this plugin folder
        intent_patterns = load_exported_from_files(
            plugin_path, 
            "Intent.py", 
            "exported_patterns",
            plugin_name=f"{plugin_name}_intents" if track_state else None,
            recursive=False
        )
        entity_patterns = load_exported_from_files(
            plugin_path, 
            "Intent.py", 
            "exported_entities",
            plugin_name=f"{plugin_name}_entities" if track_state else None,
            recursive=False
        )
        
        result["intent_patterns"] = intent_patterns
        result["entity_patterns"] = entity_patterns
        
        if track_state:
            # Store the complete plugin as one unit
            _plugin_state.add_plugin(
                plugin_name, 
                result["actions"], 
                result["intent_patterns"], 
                result["entity_patterns"],
                result["modules"]
            )
        
        logger.info(f"Successfully loaded plugin {plugin_name}: "
                   f"{len(result['actions'])} actions, "
                   f"{len(result['intent_patterns'])} intent patterns, "
                   f"{len(result['entity_patterns'])} entity patterns")
        
    except Exception as e:
        logger.error(f"Error loading plugin {plugin_name}: {e}")
    
    return result

def load_plugin_actions(plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR), track_state: bool = True) -> List[Any]:
    """
    Load and instantiate action classes from plugin folders.
    Each folder in plugins_dir is treated as a separate plugin.
    
    :param track_state: Whether to track loaded plugins in the global state
    :return: List of all action instances
    """
    plugins_root = Path(plugins_dir)
    
    if not plugins_root.exists():
        logger.warning(f"Plugins directory does not exist: {plugins_dir}")
        return []
    
    if track_state:
        # Clear existing plugins before loading new ones
        _plugin_state.clear_all()
    
    all_actions = []
    
    # Load each plugin
    for plugin_folder in plugins_root.iterdir():
        if not plugin_folder.is_dir():
            continue
            
        plugin_name = plugin_folder.name
        plugin_result = load_specific_plugin(plugin_name, plugins_dir, track_state)
        all_actions.extend(plugin_result.get("actions", []))
    
    logger.info(f"Loaded {len(all_actions)} total actions from {len(_plugin_state.get_loaded_plugin_names())} plugins")
    return all_actions

def unload_plugin(plugin_name: str) -> Dict[str, Any]:
    """
    Unload a specific plugin.
    
    :param plugin_name: Name of the plugin to unload
    :return: Dictionary with unloaded plugin data, empty if plugin wasn't loaded
    """
    try:
        if not _plugin_state.is_plugin_loaded(plugin_name):
            logger.warning(f"Plugin {plugin_name} is not currently loaded")
            return {}
        
        removed_plugin = _plugin_state.remove_plugin(plugin_name)
        logger.info(f"Successfully unloaded plugin: {plugin_name}")
        return removed_plugin
        
    except Exception as e:
        logger.error(f"Error unloading plugin {plugin_name}: {e}")
        return {}

def reload_plugin(plugin_name: str, plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR)) -> Dict[str, Any]:
    """
    Reload a specific plugin (unload then load).
    
    :param plugin_name: Name of the plugin folder
    :param plugins_dir: Base plugins directory
    :return: Dictionary with loaded components
    """
    # Unload if currently loaded
    if _plugin_state.is_plugin_loaded(plugin_name):
        unload_plugin(plugin_name)
    
    # Load the plugin
    return load_specific_plugin(plugin_name, plugins_dir, track_state=True)

def get_loaded_plugins_info() -> Dict[str, Any]:
    """
    Get information about all loaded plugins.
    
    :return: Dictionary with plugin information
    """
    plugin_state = get_plugin_state()
    loaded_plugins = plugin_state.get_loaded_plugin_names()
    
    return {
        "total_plugins": len(loaded_plugins),
        "loaded_plugins": loaded_plugins,  # Changed from "plugins" to "loaded_plugins"
        "total_actions": len(plugin_state.get_all_actions()),
        "total_intent_patterns": len(plugin_state.get_all_intent_patterns()),
        "total_entity_patterns": len(plugin_state.get_all_entity_patterns())
    }

def get_plugin_actions_for_ui(plugin_name: str) -> List[Dict[str, Any]]:
    """
    Get actions for a specific plugin formatted for UI display.
    
    :param plugin_name: Name of the plugin
    :return: List of action information dictionaries
    """
    plugin_state = get_plugin_state()
    actions = plugin_state.get_plugin_actions(plugin_name)
    
    actions_info = []
    for action in actions:
        actions_info.append({
            "name": action.__class__.__name__,
            "action_id": action.action_id,
            "display_name": getattr(action, 'display_name', action.__class__.__name__),
            "description": getattr(action, 'description', 'No description available'),
            "module": action.__module__
        })
    
    return actions_info

def get_plugin_modules_count(plugin_name: str) -> int:
    """
    Get the count of modules loaded for a specific plugin.
    
    :param plugin_name: Name of the plugin
    :return: Number of modules loaded for this plugin
    """
    plugin_state = get_plugin_state()
    plugin_info = plugin_state.get_plugin_info(plugin_name)
    
    if plugin_info:
        return len(plugin_info.get("modules", {}))
    return 0

def get_plugin_details_for_ui(plugin_name: str) -> Dict[str, Any]:
    """
    Get detailed plugin information formatted for UI display.
    
    :param plugin_name: Name of the plugin
    :return: Dictionary with plugin details for UI
    """
    plugin_info = _plugin_state.get_plugin_info(plugin_name)
    
    if not plugin_info:
        return {}
    
    # Format actions for UI
    actions_info = []
    for action in plugin_info["actions"]:
        actions_info.append({
            "name": action.__class__.__name__,
            "module": action.__module__,
            "description": getattr(action, 'description', 'No description available')
        })
    
    # Format intent patterns for UI
    intents_info = []
    for pattern in plugin_info["intent_patterns"]:
        intents_info.append({
            "pattern": str(pattern),
            "type": type(pattern).__name__
        })
    
    # Format entity patterns for UI
    entities_info = []
    for pattern in plugin_info["entity_patterns"]:
        entities_info.append({
            "pattern": str(pattern),
            "type": type(pattern).__name__
        })
    
    return {
        "name": plugin_name,
        "summary": {
            "actions": len(actions_info),
            "intents": len(intents_info),
            "entities": len(entities_info),
            "loaded_at": plugin_info["loaded_at"].strftime("%Y-%m-%d %H:%M:%S")
        },
        "details": {
            "actions": actions_info,
            "intents": intents_info,
            "entities": entities_info
        }
    }

def get_all_plugins_for_ui() -> List[Dict[str, Any]]:
    """
    Get all plugins formatted for UI display.
    
    :return: List of plugin summaries for the main list
    """
    plugins_summary = []
    for plugin_name in _plugin_state.get_loaded_plugin_names():
        plugin_details = get_plugin_details_for_ui(plugin_name)
        if plugin_details:
            plugins_summary.append({
                "name": plugin_name,
                "display_name": plugin_name.replace("_", " ").title(),
                "summary": plugin_details["summary"]
            })
    
    return plugins_summary

def unload_all_plugins() -> int:
    """
    Unload all currently loaded plugins.
    
    :return: Number of plugins that were unloaded
    """
    try:
        loaded_plugin_names = _plugin_state.get_loaded_plugin_names().copy()  # Copy to avoid modification during iteration
        unloaded_count = 0
        
        for plugin_name in loaded_plugin_names:
            if unload_plugin(plugin_name):
                unloaded_count += 1
        
        logger.info(f"Unloaded {unloaded_count} plugins")
        return unloaded_count
        
    except Exception as e:
        logger.error(f"Error unloading all plugins: {e}")
        return 0

def get_available_plugins(plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR)) -> List[str]:
    """
    Get a list of available plugin names (folder names) in the plugins directory.
    
    :return: List of plugin folder names
    """
    plugins_root = Path(plugins_dir)
    
    if not plugins_root.exists():
        logger.warning(f"Plugins directory does not exist: {plugins_dir}")
        return []
    
    available_plugins = []
    for item in plugins_root.iterdir():
        if item.is_dir():
            available_plugins.append(item.name)
    
    return available_plugins
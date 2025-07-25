import os
from utils.log_config import logger
import importlib.util
import glob
from utils.file_utils import get_resource_path
from typing import List, Tuple, Optional

INTENT_ACTION_DIR = "intent-action"

def get_plugins_dir(subdir: Optional[str] = None) -> str:
    """
    Get the path to the plugins directory.
    """
    # Assuming the plugins directory is at the same level as this script
    
    plugin_path = "plugins"

    if subdir:
        plugin_path = plugin_path + os.sep + subdir
    
    return get_resource_path(plugin_path)

def discover_action_plugin_files(plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR)):
    """
    Recursively discover all *Action.py files in the plugins/intent-action directory.
    Returns a list of file paths.
    """
    action_files = glob.glob(os.path.join(plugins_dir, "**", "*Action.py"), recursive=True)
    logger.info(f"Discovered action plugin files: {action_files}")
    return action_files

def load_actions_from_files(action_files):
    """
    Loads and instantiates action classes from a list of *Action.py files.
    Returns a list of instantiated action objects.
    """
    actions = []
    for file_path in action_files:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            logger.info(f"Imported plugin module: {module_name} from {file_path}")
            exported = getattr(module, "exported_actions", [])
            for action_cls in exported:
                try:
                    action_instance = action_cls()
                    actions.append(action_instance)
                    logger.info(f"Registered plugin action: {action_cls.__name__}")
                except Exception as e:
                    logger.error(f"Failed to instantiate action {action_cls}: {e}")
        except Exception as e:
            logger.error(f"Failed to import plugin module {module_name} from {file_path}: {e}")
    return actions

def load_plugin_intent_patterns(plugins_dir: str) -> Tuple[List, List]:
    """
    Load all intent patterns and entity patterns from plugins.
    
    Returns a tuple of (intent_patterns, entity_patterns)
    """
    intent_patterns = []
    entity_patterns = []
    
    if not os.path.exists(plugins_dir):
        logger.warning(f"Plugins directory does not exist: {plugins_dir}")
        return intent_patterns, entity_patterns
    
    for plugin_dir in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, plugin_dir)
        
        if os.path.isdir(plugin_path):
            intent_file = os.path.join(plugin_path, "Intent.py")
            
            if os.path.exists(intent_file):
                try:
                    # Import the Intent.py file
                    spec = importlib.util.spec_from_file_location("plugin_intent", intent_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Load intent patterns
                    if hasattr(module, "exported_patterns"):
                        intent_patterns.extend(module.exported_patterns)
                        logger.info(f"Loaded {len(module.exported_patterns)} patterns from {plugin_dir}")
                    
                    # Load entity patterns
                    if hasattr(module, "exported_entities"):
                        entity_patterns.extend(module.exported_entities)
                        logger.info(f"Loaded {len(module.exported_entities)} entity patterns from {plugin_dir}")
                    
                except Exception as e:
                    logger.error(f"Error loading plugin {plugin_dir}: {e}")
    
    return intent_patterns, entity_patterns
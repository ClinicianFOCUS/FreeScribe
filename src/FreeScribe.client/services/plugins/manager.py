import os
from utils.log_config import logger
import importlib.util
import glob
from utils.file_utils import get_resource_path

def get_plugins_dir():
    """
    Get the path to the plugins directory.
    """
    # Assuming the plugins directory is at the same level as this script
    return get_resource_path("plugins/intent-action")

def discover_action_plugin_files(plugins_dir: str = get_plugins_dir()):
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

def load_plugin_intent_patterns(plugins_base_dir):
    """
    Dynamically load SpacyIntentPattern lists from all *Intent.py files in plugins/intent-action/**/
    """
    patterns = []
    # Recursively find all *Intent.py files
    pattern_files = glob.glob(os.path.join(plugins_base_dir, "**", "*Intent.py"), recursive=True)
    for file_path in pattern_files:
        module_name = os.path.splitext(os.path.basename(file_path))[0]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "exported_patterns"):
            logger.info(f"Loaded pattern: {module_name} from {file_path}")
            patterns.extend(module.exported_patterns)
    return patterns
import os
from pathlib import Path
from utils.log_config import logger
import importlib.util
import glob
from utils.file_utils import get_resource_path
from typing import List, Tuple, Optional, TypeVar, Any

T = TypeVar("T")

INTENT_ACTION_DIR = "intent-action"

def load_exported_from_files(
    base_dir: Path, 
    file_pattern: str,
    export_name: str
) -> List[T]:
    """
    Recursively load `export_name` from all files matching `file_pattern` under `base_dir`.
    Returns a flat list of whatever was in `module.<export_name>`.
    """
    results: List[T] = []
    for file in base_dir.rglob(file_pattern):
        spec = importlib.util.spec_from_file_location(file.stem, file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)  # type: ignore
            results.extend(getattr(module, export_name, []))
            logger.debug(f"Loaded {export_name} from {file}")
        except Exception as e:
            logger.error(f"Failed to load {export_name} from {file}: {e}")
    return results

def get_plugins_dir(subdir: Optional[str] = None) -> str:
    """
    Get the path to the plugins directory.
    """
    # Assuming the plugins directory is at the same level as this script
    
    plugin_path = "plugins"

    if subdir:
        plugin_path = plugin_path + os.sep + subdir
    
    return get_resource_path(plugin_path)

def load_plugin_actions(plugins_dir: str = get_plugins_dir(INTENT_ACTION_DIR)):
    """
    Load and instantiate action classes from plugin files.
    Returns a list of instantiated action objects.
    """
    plugins_root = Path(plugins_dir)
    action_classes = load_exported_from_files(plugins_root, "*Action.py", "exported_actions")
    
    actions = []
    for cls in action_classes:
        try:
            action_instance = cls()
            actions.append(action_instance)
        except Exception as e:
            logger.error(f"Failed to instantiate action {cls}: {e}")
    
    logger.info(f"Loaded {len(actions)} plugin actions")
    return actions

def load_plugin_intent_patterns(plugins_dir: str) -> Tuple[List, List]:
    """
    Load all intent patterns and entity patterns from plugins.
    
    Returns a tuple of (intent_patterns, entity_patterns)
    """
    if not os.path.exists(plugins_dir):
        logger.warning(f"Plugins directory does not exist: {plugins_dir}")
        return [], []
    
    plugins_root = Path(plugins_dir)
    
    # Load intent patterns and entity patterns using the reusable helper
    intent_patterns = load_exported_from_files(plugins_root, "Intent.py", "exported_patterns")
    entity_patterns = load_exported_from_files(plugins_root, "Intent.py", "exported_entities")
    
    logger.info(f"Loaded {len(intent_patterns)} intent patterns and {len(entity_patterns)} entity patterns")
    return intent_patterns, entity_patterns
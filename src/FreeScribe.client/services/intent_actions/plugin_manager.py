import os
import threading
import datetime
from pathlib import Path
from utils.log_config import logger
import importlib.util
from utils.file_utils import get_resource_path
from typing import List, Tuple, Optional, TypeVar, Any, Dict
import tkinter as tk
from tkinter import messagebox
import traceback

T = TypeVar("T")

INTENT_ACTION_DIR = "intent-action"

class PluginState:
    """Manages the state of loaded plugins."""
    
    def __init__(self):
        self._loaded_plugins: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def add_module(self, plugin_name: str, module_name: str, module: Any) -> None:
        """Add a module to the tracking (for cleanup purposes)."""
        with self._lock:
            if plugin_name in self._loaded_plugins:
                if "modules" not in self._loaded_plugins[plugin_name]:
                    self._loaded_plugins[plugin_name]["modules"] = {}
                self._loaded_plugins[plugin_name]["modules"][module_name] = module
    
    def add_plugin(self, plugin_name: str, actions: List[Any], intent_patterns: List[Any], entity_patterns: List[Any], modules: Dict[str, Any]) -> None:
        """Add a complete plugin to the loaded state."""
        with self._lock:
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

# Track which plugins have already shown error dialogs to prevent duplicates
_error_dialogs_shown = set()

# Track errors for each plugin to consolidate them
_plugin_errors: Dict[str, List[Dict[str, str]]] = {}

def get_plugin_state() -> PluginState:
    """Get the global plugin state instance."""
    return _plugin_state

def add_plugin_error(plugin_name: str, file_path: str, error: Exception, error_type: str = "Loading") -> None:
    """
    Add an error to the plugin's error list for later consolidation.
    
    :param plugin_name: Name of the plugin that failed
    :param file_path: Path to the file that caused the error
    :param error: The exception that occurred
    :param error_type: Type of error (e.g., "Action Loading", "Intent Loading", etc.)
    """
    if plugin_name not in _plugin_errors:
        _plugin_errors[plugin_name] = []
    
    error_info = {
        "type": error_type,
        "file": file_path,
        "error_class": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc()
    }
    
    _plugin_errors[plugin_name].append(error_info)
    logger.error(f"Added {error_type} error for plugin {plugin_name}: {error}")

def show_consolidated_plugin_errors(plugin_name: str) -> None:
    """
    Show a consolidated error dialog for all errors encountered while loading a plugin.
    
    :param plugin_name: Name of the plugin that had errors
    """
    if plugin_name not in _plugin_errors or not _plugin_errors[plugin_name]:
        return
    
    # Check if we've already shown an error dialog for this plugin
    if plugin_name in _error_dialogs_shown:
        logger.debug(f"Error dialog already shown for plugin {plugin_name}, skipping duplicate")
        return
    
    # Mark this plugin as having shown an error dialog
    _error_dialogs_shown.add(plugin_name)
    
    try:
        errors = _plugin_errors[plugin_name]
        
        # Create the consolidated error message
        error_message = f"Plugin '{plugin_name}' failed to load with {len(errors)} error(s):\n\n"
        
        for i, error_info in enumerate(errors, 1):
            error_message += f"=== Error {i}: {error_info['type']} ===\n"
            error_message += f"File: {error_info['file']}\n"
            error_message += f"Error: {error_info['error_class']}: {error_info['error_message']}\n\n"
            error_message += f"Traceback:\n{error_info['traceback']}\n"
            error_message += "=" * 60 + "\n\n"
        
        # Get the root window if it exists
        try:
            # Try to get the root window
            root = tk._default_root
            if root is None:
                # If no default root, get all windows and find the root
                for widget in tk._default_root.winfo_children() if tk._default_root else []:
                    if isinstance(widget, tk.Tk):
                        root = widget
                        break
        except Exception as e:
            root = None
            logger.exception(f"Error getting root window: {e}")

        # Create a popup window with scrollable text
        error_window = tk.Toplevel(root) if root else tk.Toplevel()
        error_window.title(f"Plugin Load Errors - {plugin_name}")
        error_window.geometry("700x500")
        error_window.resizable(True, True)
        
        # Make the window modal and on top
        if root:
            error_window.transient(root)
        error_window.grab_set()
        error_window.lift()  # Bring to front
        error_window.attributes('-topmost', True)  # Stay on top
        error_window.focus_force()  # Force focus
        
        # Main label
        main_label = tk.Label(error_window, 
                             text=f"Plugin '{plugin_name}' failed to load with {len(errors)} error(s) and has been removed.",
                             font=("Arial", 12, "bold"),
                             fg="red")
        main_label.pack(pady=10)
        
        # Frame for the text area and scrollbar
        text_frame = tk.Frame(error_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Text widget with scrollbar
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Courier", 9))
        scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        # Pack the text widget and scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Insert the error message
        text_widget.insert(tk.END, error_message)
        text_widget.config(state=tk.DISABLED)
        
        # OK button that also cleans up the tracking
        def on_ok():
            _error_dialogs_shown.discard(plugin_name)  # Remove from tracking when dialog is closed
            _plugin_errors.pop(plugin_name, None)  # Clear the errors for this plugin
            error_window.destroy()
        
        ok_button = tk.Button(error_window, text="OK", command=on_ok)
        ok_button.pack(pady=10)
        
        # Center the window on the screen (or relative to parent if available)
        error_window.update_idletasks()
        
        if root:
            # Center relative to the root window
            root_x = root.winfo_x()
            root_y = root.winfo_y()
            root_width = root.winfo_width()
            root_height = root.winfo_height()
            
            dialog_width = error_window.winfo_width()
            dialog_height = error_window.winfo_height()
            
            # Center on the root window
            x = root_x + (root_width - dialog_width) // 2
            y = root_y + (root_height - dialog_height) // 2
        else:
            # Center on screen
            x = (error_window.winfo_screenwidth() // 2) - (error_window.winfo_width() // 2)
            y = (error_window.winfo_screenheight() // 2) - (error_window.winfo_height() // 2)
        
        error_window.geometry(f"+{x}+{y}")
        
        # Ensure it's still on top after positioning
        error_window.lift()
        error_window.attributes('-topmost', True)
        
        # Allow user to disable topmost after a short delay (so they can interact with other windows if needed)
        def disable_topmost():
            try:
                error_window.attributes('-topmost', False)
            except:
                pass  # Window might be destroyed
        
        error_window.after(3000, disable_topmost)  # Remove topmost after 3 seconds
        
        logger.error(f"Consolidated plugin error dialog shown for {plugin_name} with {len(errors)} errors")
        
    except Exception as dialog_error:
        # Fallback to simple messagebox if the custom dialog fails
        logger.exception(f"Failed to show consolidated error dialog: {dialog_error}")
        try:
            error_summary = f"Plugin '{plugin_name}' failed to load with {len(_plugin_errors.get(plugin_name, []))} error(s)"
            messagebox.showerror(f"Plugin Error - {plugin_name}", error_summary)
        except Exception as fallback_error:
            logger.exception(f"Even fallback messagebox failed: {fallback_error}")
        finally:
            # Remove from tracking even if dialog failed
            _error_dialogs_shown.discard(plugin_name)
            _plugin_errors.pop(plugin_name, None)

def show_plugin_error_dialog(plugin_name: str, file_path: str, error: Exception) -> None:
    """
    Legacy function for backward compatibility. Now adds to consolidated errors.
    """
    add_plugin_error(plugin_name, file_path, error, "General Loading")

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
            
            # Validate that exported_items is iterable
            try:
                iter(exported_items)
                results.extend(exported_items)
            except TypeError:
                logger.exception(f"Exported {export_name} from {file} is not iterable (type: {type(exported_items)})")
                continue
            
            # Track the module in plugin state if plugin_name is provided
            if plugin_name:
                _plugin_state.add_module(plugin_name, f"{plugin_name}_{file.stem}", module)
            
            logger.debug(f"Loaded {export_name} from {file}")
            
        except SyntaxError as e:
            logger.exception(f"Syntax error in {file}: {e}")
            # Add to consolidated errors but don't crash
            if plugin_name:
                add_plugin_error(plugin_name, str(file), e, f"Syntax Error in {export_name}")
                # Remove the plugin from the loaded state if it was partially loaded
                _plugin_state.remove_plugin(plugin_name)
            # Continue processing other files instead of raising
            continue
            
        except Exception as e:
            logger.exception(f"Failed to load {export_name} from {file}: {e}")
            
            # Add to consolidated errors and remove plugin if plugin_name is provided
            if plugin_name:
                add_plugin_error(plugin_name, str(file), e, f"Loading {export_name}")
                # Remove the plugin from the loaded state if it was partially loaded
                _plugin_state.remove_plugin(plugin_name)
            
            # Continue processing other files instead of raising
            continue
            
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
    failed_plugins = []
    
    # Iterate through each plugin folder
    for plugin_folder in plugins_root.iterdir():
        if not plugin_folder.is_dir():
            continue
            
        plugin_name = plugin_folder.name
        logger.info(f"Loading intent patterns from plugin: {plugin_name}")
        
        try:
            # Load intent patterns from this plugin folder - use main plugin name, not separate tracking
            intent_patterns = load_exported_from_files(
                plugin_folder, 
                "Intent.py", 
                "exported_patterns",
                plugin_name=plugin_name if track_state else None,  
                recursive=False
            )
            
            # Load entity patterns from this plugin folder - use main plugin name, not separate tracking
            entity_patterns = load_exported_from_files(
                plugin_folder, 
                "Intent.py", 
                "exported_entities",
                plugin_name=plugin_name if track_state else None,  
                recursive=False
            )
            
            # Only add patterns if we successfully loaded them
            if intent_patterns:
                all_intent_patterns.extend(intent_patterns)
                logger.info(f"Loaded {len(intent_patterns)} intent patterns from {plugin_name}")
            
            if entity_patterns:
                all_entity_patterns.extend(entity_patterns)
                logger.info(f"Loaded {len(entity_patterns)} entity patterns from {plugin_name}")
                
        except Exception as e:
            logger.exception(f"Failed to load patterns from plugin {plugin_name}: {e}")
            failed_plugins.append(plugin_name)
            
            # Only show error dialog if one hasn't been shown already for this plugin
            if plugin_name not in _error_dialogs_shown:
                try:
                    intent_file_path = plugin_folder / "Intent.py"
                    if intent_file_path.exists():
                        show_plugin_error_dialog(plugin_name, str(intent_file_path), e)
                    else:
                        show_plugin_error_dialog(plugin_name, f"{plugin_folder}/Intent.py (file not found)", e)
                        
                    # Remove only the main plugin from state
                    _plugin_state.remove_plugin(plugin_name)
                    
                except Exception as dialog_error:
                    logger.exception(f"Failed to show error dialog for Intent.py failure: {dialog_error}")

            # Continue with other plugins instead of crashing
            continue
    
    if failed_plugins:
        logger.warning(f"Failed to load patterns from {len(failed_plugins)} plugins: {failed_plugins}")
    
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
    
    # Clear any previous errors for this plugin
    _plugin_errors.pop(plugin_name, None)
    
    result = {
        "name": plugin_name,
        "actions": [],
        "intent_patterns": [],
        "entity_patterns": [],
        "modules": {}
    }
    
    plugin_had_errors = False
    
    try:
        # Load actions from this plugin folder
        try:
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
                    logger.exception(f"Failed to instantiate action {cls} from {plugin_name}: {e}")
                    if track_state:
                        add_plugin_error(plugin_name, f"Action class: {cls.__name__}", e, "Action Instantiation")
                        plugin_had_errors = True
                    # Continue with other actions instead of failing the entire plugin
                    continue
                    
        except Exception as e:
            logger.exception(f"Failed to load actions from plugin {plugin_name}: {e}")
            # Add to consolidated errors for Action.py loading failures
            if track_state:
                try:
                    action_file_pattern = list(plugin_path.glob("*Action.py"))
                    action_file_path = str(action_file_pattern[0]) if action_file_pattern else f"{plugin_path}/*Action.py (no files found)"
                    add_plugin_error(plugin_name, action_file_path, e, "Action File Loading")
                    plugin_had_errors = True
                except Exception:
                    pass
        
        # Load intent patterns from this plugin folder
        try:
            intent_patterns = load_exported_from_files(
                plugin_path, 
                "Intent.py", 
                "exported_patterns",
                plugin_name=plugin_name if track_state else None,  
                recursive=False
            )
            entity_patterns = load_exported_from_files(
                plugin_path, 
                "Intent.py", 
                "exported_entities",
                plugin_name=plugin_name if track_state else None,  
                recursive=False
            )
            
            result["intent_patterns"] = intent_patterns
            result["entity_patterns"] = entity_patterns
            
        except Exception as e:
            logger.exception(f"Failed to load intent/entity patterns from plugin {plugin_name}: {e}")
            # Add to consolidated errors for Intent.py loading failures
            if track_state:
                try:
                    intent_file_path = plugin_path / "Intent.py"
                    add_plugin_error(plugin_name, str(intent_file_path), e, "Intent/Entity Pattern Loading")
                    plugin_had_errors = True
                except Exception:
                    pass
        
        # Check if any errors occurred during loading
        if plugin_name in _plugin_errors and _plugin_errors[plugin_name]:
            plugin_had_errors = True
        
        # Show consolidated error dialog if there were any errors
        if plugin_had_errors and track_state:
            show_consolidated_plugin_errors(plugin_name)
            return {}  # Return empty result for failed plugin
        
        if track_state and (result["actions"] or result["intent_patterns"] or result["entity_patterns"]):
            # Only store the plugin if we loaded something successfully
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
        logger.exception(f"Error loading plugin {plugin_name}: {e}")
        # Add to consolidated errors for general plugin loading failures
        if track_state:
            add_plugin_error(plugin_name, str(plugin_path), e, "General Plugin Loading")
            show_consolidated_plugin_errors(plugin_name)
            _plugin_state.remove_plugin(plugin_name)
        return {}
    
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
        # Also clear the error dialog tracking and plugin errors
        _error_dialogs_shown.clear()
        _plugin_errors.clear()
    
    all_actions = []
    failed_plugins = []
    
    # Load each plugin
    for plugin_folder in plugins_root.iterdir():
        if not plugin_folder.is_dir():
            continue
            
        plugin_name = plugin_folder.name
        try:
            plugin_result = load_specific_plugin(plugin_name, plugins_dir, track_state)
            if plugin_result:  # Only add actions if plugin loaded successfully
                all_actions.extend(plugin_result.get("actions", []))
            else:
                failed_plugins.append(plugin_name)
        except Exception as e:
            logger.exception(f"Failed to load plugin {plugin_name}: {e}")
            failed_plugins.append(plugin_name)
            continue
    
    successful_plugins = len(_plugin_state.get_loaded_plugin_names())
    logger.info(f"Loaded {len(all_actions)} total actions from {successful_plugins} plugins")
    
    if failed_plugins:
        logger.warning(f"Failed to load {len(failed_plugins)} plugins: {failed_plugins}")
    
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
        logger.exception(f"Error unloading plugin {plugin_name}: {e}")
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
        "loaded_plugins": loaded_plugins,
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
            "action_id": getattr(action, 'action_id', action.__class__.__name__),
            "display_name": getattr(action, 'display_name', action.__class__.__name__),
            "description": getattr(action, 'description', 'No description available'),
            "module": action.__module__
        })
    
    return actions_info

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
        logger.exception(f"Error unloading all plugins: {e}")
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

def clean_up_duplicate_plugin_entries():
    """
    Clean up any duplicate plugin entries that might exist from previous versions.
    This removes entries like 'HelloWorld_intents' and 'HelloWorld_entities' if
    a main 'HelloWorld' entry exists.
    """
    try:
        plugin_state = get_plugin_state()
        loaded_plugins = plugin_state.get_loaded_plugin_names().copy()
        
        # Find main plugins and their potential duplicates
        main_plugins = set()
        duplicate_entries = []
        
        for plugin_name in loaded_plugins:
            if plugin_name.endswith('_intents') or plugin_name.endswith('_entities'):
                # This is a potential duplicate entry
                base_name = plugin_name.replace('_intents', '').replace('_entities', '')
                if base_name in loaded_plugins:
                    # Main plugin exists, mark this as a duplicate
                    duplicate_entries.append(plugin_name)
                else:
                    # Main plugin doesn't exist, this might be a legitimate entry
                    main_plugins.add(base_name)
        
        # Remove duplicate entries
        for duplicate in duplicate_entries:
            plugin_state.remove_plugin(duplicate)
            logger.info(f"Cleaned up duplicate plugin entry: {duplicate}")
        
        if duplicate_entries:
            logger.info(f"Cleaned up {len(duplicate_entries)} duplicate plugin entries")
            
    except Exception as e:
        logger.exception(f"Error cleaning up duplicate plugin entries: {e}")

class PluginService:
    """Service class for managing plugins with reduced boilerplate."""
    
    def __init__(self, plugin_dir: Path):
        self.plugin_dir = plugin_dir

    def load_all(self):
        """Load all plugins from the plugin directory."""
        load_plugin_actions(str(self.plugin_dir))

    def load(self, name: str) -> Dict[str, Any]:
        """Load a specific plugin by name."""
        return load_specific_plugin(name, str(self.plugin_dir))

    def unload(self, name: str) -> Dict[str, Any]:
        """Unload a specific plugin by name."""
        return unload_plugin(name)

    def reload(self, name: Optional[str] = None) -> bool:
        """Reload a specific plugin or all plugins if name is None.
        
        Returns True if reload succeeded, False otherwise.
        """
        try:
            if name:
                result = reload_plugin(name, str(self.plugin_dir))
                return bool(result)
            load_plugin_actions(str(self.plugin_dir))
            return True
        except Exception as e:
            logger.exception(f"Error reloading plugin(s): {e}")
            return False

    def state(self):
        """Get the plugin state instance."""
        return get_plugin_state()

    def get_all_actions(self) -> List[Any]:
        """Get all loaded actions from plugins."""
        return self.state().get_all_actions()

    def get_info(self) -> Dict[str, Any]:
        """Get information about all loaded plugins."""
        return get_loaded_plugins_info()

    def get_details(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plugin."""
        return get_plugin_details_for_ui(name)

    def list_for_ui(self) -> List[Dict[str, Any]]:
        """Get all plugins formatted for UI display."""
        return get_all_plugins_for_ui()
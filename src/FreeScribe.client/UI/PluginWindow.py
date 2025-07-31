import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import subprocess
from pathlib import Path
from threading import Thread
from typing import Dict, Any, Optional
from utils.log_config import logger
from services.intent_actions.plugin_manager import (
    get_plugin_state,
    load_specific_plugin,
    unload_plugin,
    reload_plugin,
    get_loaded_plugins_info,
    unload_all_plugins,
    get_plugins_dir,
    INTENT_ACTION_DIR,
    get_plugin_modules_count,
    get_plugin_details_for_ui
)

class PluginManagerWindow:
    """Plugin management UI window for loading, unloading, and managing plugins."""
    
    def __init__(self, parent: tk.Tk, intent_manager=None):
        """
        Initialize the plugin manager window.
        
        :param parent: Parent window
        :param intent_manager: Reference to IntentActionManager for coordination
        """
        self.parent = parent
        self.intent_manager = intent_manager
        self.window = None
        self.plugin_listbox = None
        self.info_text = None
        self.status_label = None
        self.refresh_needed = False
        
    def show(self):
        """Show the plugin manager window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.create_window()
        self.refresh_plugin_list()
        
    def create_window(self):
        """Create the plugin manager window UI."""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Plugin Manager")
        self.window.geometry("800x600")
        self.window.resizable(True, True)
        
        # Make window modal
        self.window.transient(self.parent)
        self.window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Plugin Manager", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        
        # Left panel - Plugin list
        left_frame = ttk.LabelFrame(main_frame, text="Loaded Plugins", padding="5")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        
        # Plugin listbox with scrollbar
        listbox_frame = ttk.Frame(left_frame)
        listbox_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.plugin_listbox = tk.Listbox(listbox_frame, selectmode=tk.SINGLE)
        self.plugin_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.plugin_listbox.bind('<<ListboxSelect>>', self.on_plugin_select)
        
        # Scrollbar for listbox
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.plugin_listbox.yview)
        listbox_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.plugin_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        
        # Plugin action buttons
        button_frame = ttk.Frame(left_frame)
        button_frame.grid(row=1, column=0, pady=(5, 0), sticky=(tk.W, tk.E))
        
        ttk.Button(button_frame, text="Load Plugin", command=self.load_plugin_dialog).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Unload Selected", command=self.unload_selected_plugin).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Reload Selected", command=self.reload_selected_plugin).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Refresh", command=self.refresh_plugin_list).pack(side=tk.LEFT, padx=(0, 5))
        
        # Unload all button (with warning color)
        unload_all_btn = ttk.Button(button_frame, text="Unload All", command=self.unload_all_plugins)
        unload_all_btn.pack(side=tk.RIGHT)
        
        # Right panel - Plugin information
        right_frame = ttk.LabelFrame(main_frame, text="Plugin Information", padding="5")
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        
        # Info text with scrollbar
        info_frame = ttk.Frame(right_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(0, weight=1)
        
        self.info_text = tk.Text(info_frame, wrap=tk.WORD, state=tk.DISABLED, width=40)
        self.info_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for info text
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        info_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.info_text.configure(yscrollcommand=info_scrollbar.set)
        
        # Bottom panel - Status and actions
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky=(tk.W, tk.E))
        bottom_frame.columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ttk.Label(bottom_frame, text="Ready", foreground="green")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        # Bottom buttons
        button_bottom_frame = ttk.Frame(bottom_frame)
        button_bottom_frame.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Button(button_bottom_frame, text="Browse Plugin Directory", command=self.browse_plugin_directory).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_bottom_frame, text="Close", command=self.close_window).pack(side=tk.LEFT)
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
    
    def _confirm_then(self, title: str, msg: str, func, *args):
        """Show confirmation dialog and execute function if confirmed."""
        if messagebox.askyesno(title, msg):
            func(*args)

    def _run_task(self,
                  title: str,
                  task_fn,
                  args: tuple=(),
                  success_msg: str = None,
                  on_success=None,
                  refresh: bool = True):
        """Run task_fn(*args) in a thread, update status, call on_success(result)."""
        def _worker():
            try:
                self.set_status(f"{title}...", "blue")
                result = task_fn(*args)
                if success_msg:
                    if callable(success_msg):
                        msg = success_msg(result)
                    else:
                        msg = success_msg.format(result=result)
                    self.set_status(msg, "green")
                if on_success:
                    on_success(result)
                if refresh:
                    self.window.after(100, self.refresh_plugin_list)
            except Exception as e:
                logger.error(f"{title} failed: {e}")
                self.window.after(0, lambda: self.set_status(f"Error {title}: {e}", "red"))

        Thread(target=_worker, daemon=True).start()
        
    def refresh_plugin_list(self):
        """Refresh the list of loaded plugins."""
        try:
            self.set_status("Refreshing plugin list...", "blue")
            
            # Clear current list
            self.plugin_listbox.delete(0, tk.END)
            
            # Get plugin info
            plugin_info = get_loaded_plugins_info()
            loaded_plugins = plugin_info.get("loaded_plugins", [])
            logger.debug(f"Plugin window refresh: found {len(loaded_plugins)} plugins: {loaded_plugins}")
            
            # Add plugins to listbox
            for plugin_name in sorted(loaded_plugins):
                self.plugin_listbox.insert(tk.END, plugin_name)
            
            # Update info display
            self.update_general_info(plugin_info)
            
            self.set_status(f"Loaded {len(loaded_plugins)} plugins", "green")
            
        except Exception as e:
            logger.error(f"Error refreshing plugin list: {e}")
            self.set_status(f"Error: {str(e)}", "red")
    
    def on_plugin_select(self, event):
        """Handle plugin selection in the listbox."""
        selection = self.plugin_listbox.curselection()
        if not selection:
            return
            
        plugin_name = self.plugin_listbox.get(selection[0])
        self.update_plugin_info(plugin_name)
    
    def update_plugin_info(self, plugin_name: str):
        """Update the plugin information display."""
        try:
            plugin_state = get_plugin_state()
            
            # Clear and enable text widget
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            
            # Get plugin details
            plugin_details = get_plugin_details_for_ui(plugin_name)
            
            if not plugin_details:
                self.info_text.insert(tk.END, f"No information available for plugin: {plugin_name}")
                self.info_text.config(state=tk.DISABLED)
                return
            
            # Display plugin information
            info_lines = [
                f"Plugin: {plugin_name}",
                "=" * 50,
                "",
                "Summary:",
                "-" * 20,
                f"Actions: {plugin_details['summary']['actions']}",
                f"Intent Patterns: {plugin_details['summary']['intents']}",
                f"Entity Patterns: {plugin_details['summary']['entities']}",
                f"Loaded At: {plugin_details['summary']['loaded_at']}",
                ""
            ]
            
            # Display actions
            if plugin_details['details']['actions']:
                info_lines.extend([
                    f"Actions ({len(plugin_details['details']['actions'])}):",
                    "-" * 20
                ])
                for i, action in enumerate(plugin_details['details']['actions'], 1):
                    info_lines.extend([
                        f"{i}. {action['name']}",
                        f"   Description: {action['description']}",
                        f"   Module: {action['module']}",
                        ""
                    ])
            else:
                info_lines.extend(["Actions:", "-" * 20, "No actions found.", ""])
            
            # Display intent patterns
            if plugin_details['details']['intents']:
                info_lines.extend([
                    f"Intent Patterns ({len(plugin_details['details']['intents'])}):",
                    "-" * 20
                ])
                for i, pattern in enumerate(plugin_details['details']['intents'], 1):
                    info_lines.extend([
                        f"{i}. {pattern['pattern']} ({pattern['type']})",
                    ])
                info_lines.append("")
            else:
                info_lines.extend(["Intent Patterns:", "-" * 20, "No intent patterns found.", ""])
            
            # Display entity patterns
            if plugin_details['details']['entities']:
                info_lines.extend([
                    f"Entity Patterns ({len(plugin_details['details']['entities'])}):",
                    "-" * 20
                ])
                for i, pattern in enumerate(plugin_details['details']['entities'], 1):
                    info_lines.extend([
                        f"{i}. {pattern['pattern']} ({pattern['type']})",
                    ])
                info_lines.append("")
            else:
                info_lines.extend(["Entity Patterns:", "-" * 20, "No entity patterns found.", ""])
            
            # Plugin state information
            info_lines.extend([
                "Plugin State:",
                "-" * 20,
                f"Is Loaded: {plugin_state.is_plugin_loaded(plugin_name)}",
                f"Module Count: {get_plugin_modules_count(plugin_name)}"
            ])
            
            # Insert text
            self.info_text.insert(tk.END, "\n".join(info_lines))
            self.info_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error updating plugin info for {plugin_name}: {e}")
            self.set_status(f"Error getting plugin info: {str(e)}", "red")
    
    def update_general_info(self, plugin_info: Dict[str, Any]):
        """Update the general plugin information display."""
        try:
            # Clear and enable text widget
            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            
            # Display general information
            info_lines = [
                "Plugin System Overview",
                "=" * 50,
                "",
                f"Total Loaded Plugins: {plugin_info.get('total_plugins', 0)}",
                f"Total Actions: {plugin_info.get('total_actions', 0)}",
                f"Total Intent Patterns: {plugin_info.get('total_intent_patterns', 0)}",
                f"Total Entity Patterns: {plugin_info.get('total_entity_patterns', 0)}",
                "",
                "Loaded Plugins:",
                "-" * 20
            ]
            
            loaded_plugins = plugin_info.get('loaded_plugins', [])
            for plugin_name in sorted(loaded_plugins):
                info_lines.append(f"• {plugin_name}")
            
            if not loaded_plugins:
                info_lines.append("No plugins currently loaded.")
            
            info_lines.extend([
                "",
                "Plugin Directory:",
                "-" * 20,
                get_plugins_dir(INTENT_ACTION_DIR),
                "",
                "Select a plugin from the list to view detailed information."
            ])
            
            # Insert text
            self.info_text.insert(tk.END, "\n".join(info_lines))
            self.info_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error updating general info: {e}")
    
    def load_plugin_dialog(self):
        """Show dialog to load a new plugin."""
        try:
            # Start from the plugins directory
            initial_dir = get_plugins_dir(INTENT_ACTION_DIR)
            
            plugin_dir = filedialog.askdirectory(
                title="Select Plugin Directory",
                initialdir=initial_dir
            )
            
            if not plugin_dir:
                return
                
            # Extract plugin name from the directory path
            plugin_name = Path(plugin_dir).name
            self.load_plugin_threaded(plugin_name)
            
        except Exception as e:
            logger.error(f"Error in load plugin dialog: {e}")
            self.set_status(f"Error: {str(e)}", "red")
    
    def load_plugin_threaded(self, plugin_name: str):
        """Load a plugin in a separate thread."""
        def task_fn(name):
            if self.intent_manager:
                return self.intent_manager.add_plugin(name)
            else:
                result = load_specific_plugin(name)
                return bool(result.get("name"))
                
        self._run_task(
            title=f"Loading {plugin_name}",
            task_fn=task_fn,
            args=(plugin_name,),
            success_msg=f"Successfully loaded {plugin_name}"
        )
    
    def unload_selected_plugin(self):
        """Unload the selected plugin."""
        selection = self.plugin_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a plugin to unload.")
            return
            
        plugin_name = self.plugin_listbox.get(selection[0])
        self._confirm_then(
            "Confirm Unload",
            f"Are you sure you want to unload '{plugin_name}'?",
            self.unload_plugin_threaded,
            plugin_name
        )
    
    def unload_plugin_threaded(self, plugin_name: str):
        """Unload a plugin in a separate thread."""
        def task_fn(name):
            if self.intent_manager:
                return self.intent_manager.remove_plugin(name)
            else:
                return unload_plugin(name)
                
        self._run_task(
            title=f"Unloading {plugin_name}",
            task_fn=task_fn,
            args=(plugin_name,),
            success_msg=f"Unloaded {plugin_name}"
        )
    
    def reload_selected_plugin(self):
        """Reload the selected plugin."""
        selection = self.plugin_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a plugin to reload.")
            return
            
        self.reload_plugin_threaded(self.plugin_listbox.get(selection[0]))
    
    def reload_plugin_threaded(self, plugin_name: str):
        """Reload a plugin in a separate thread."""
        def task_fn(name):
            if self.intent_manager:
                return self.intent_manager.reload_plugin(name)
            else:
                result = reload_plugin(name)
                return bool(result.get("name"))
                
        self._run_task(
            title=f"Reloading {plugin_name}",
            task_fn=task_fn,
            args=(plugin_name,),
            success_msg=f"Successfully reloaded {plugin_name}"
        )
    
    def unload_all_plugins(self):
        """Unload all plugins after confirmation."""
        plugin_info = get_loaded_plugins_info()
        plugin_count = plugin_info.get('total_plugins', 0)
        
        if plugin_count == 0:
            messagebox.showinfo("No Plugins", "No plugins are currently loaded.")
            return
            
        self._confirm_then(
            "Confirm Unload All",
            f"Unload all {plugin_count} plugins? This cannot be undone.",
            self._do_unload_all
        )

    def _do_unload_all(self):
        """Execute unload all plugins operation."""
        def task_fn():
            unloaded_count = unload_all_plugins()
            # Reinitialize the intent manager to clear patterns after unloading all plugins
            if self.intent_manager:
                self.intent_manager._reinit_recognizer()
            return unloaded_count
            
        def format_success(result):
            return f"Successfully unloaded {result} plugins"
            
        self._run_task(
            title="Unloading all plugins",
            task_fn=task_fn,
            success_msg=format_success
        )
    
    def browse_plugin_directory(self):
        """Open the plugin directory in file explorer."""
        try:
            plugin_dir = get_plugins_dir(INTENT_ACTION_DIR)
            if os.name == 'nt':  # Windows
                subprocess.run(["explorer", plugin_dir], check=False)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(["open", plugin_dir], check=False)
            else:  # Linux and other Unix-like systems
                subprocess.run(["xdg-open", plugin_dir], check=False)
        except Exception as e:
            logger.error(f"Error opening plugin directory: {e}")
            messagebox.showerror("Error", f"Could not open plugin directory: {str(e)}")
    
    def set_status(self, message: str, color: str = "black"):
        """Set the status message with color."""
        try:
            if self.status_label and self.status_label.winfo_exists():
                self.status_label.config(text=message, foreground=color)
                self.window.update_idletasks()
        except tk.TclError:
            # Widget might be destroyed
            pass
    
    def close_window(self):
        """Close the plugin manager window."""
        try:
            if self.window:
                self.window.grab_release()
                self.window.destroy()
                self.window = None
        except tk.TclError:
            # Window might already be destroyed
            pass

# Example usage and integration helper
def show_plugin_manager(parent_window: tk.Tk, intent_manager=None):
    """
    Convenience function to show the plugin manager window.
    
    :param parent_window: Parent tkinter window
    :param intent_manager: Optional IntentActionManager instance
    """
    manager = PluginManagerWindow(parent_window, intent_manager)
    manager.show()
    return manager
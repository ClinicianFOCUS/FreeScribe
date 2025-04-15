import datetime
import tkinter as tk
from tkinter import messagebox as messagebox

import pyperclip

from UI.Widgets.PopupBox import PopupBox

from utils.log_config import logger
import sys
from client_modules.app_context import AppContext, AppConstants, AppUIComponents
from utils.window_utils import add_min_max, remove_min_max


# This runs before on_closing, if not confirmed, nothing should be changed
def confirm_exit_and_destroy():
    """Show confirmation dialog before exiting the application.

    Displays a warning message about temporary note history being cleared on exit.
    If the user confirms, triggers the window close event. If canceled, the application
    remains open.

    .. note::
        This function is bound to the window's close button (WM_DELETE_WINDOW protocol).

    .. warning::
        All temporary note history will be permanently cleared when the application closes.

    :returns: None
    :rtype: None
    """


    if messagebox.askokcancel(
            "Confirm Exit",
            "Warning: Temporary Note History will be cleared when app closes.\n\n"
            "Please make sure you have copied your important notes elsewhere "
            "before closing.\n\n"
            "Do you still want to exit?"
    ):
        try:
            AppContext.root.quit()
            AppContext.root.destroy()
            sys.exit(0)
        except Exception as e:
            logger.exception(str(e))
            sys.exit(1)


def update_gui(text):
    AppUIComponents.user_input.scrolled_text.insert(tk.END, text + '\n')
    AppUIComponents.user_input.scrolled_text.see(tk.END)


def disable_recording_ui_elements():
    AppContext.window.disable_settings_menu()
    AppUIComponents.user_input.scrolled_text.configure(state='disabled')
    AppUIComponents.send_button.config(state='disabled')
    #hidding the AI Scribe button actions
    #toggle_button.config(state='disabled')
    AppUIComponents.upload_button.config(state='disabled')
    AppUIComponents.response_display.scrolled_text.configure(state='disabled')
    AppUIComponents.timestamp_listbox.config(state='disabled')
    AppUIComponents.clear_button.config(state='disabled')
    AppUIComponents.mic_test.set_mic_test_state(False)


def enable_recording_ui_elements():
    AppContext.window.enable_settings_menu()
    AppUIComponents.user_input.scrolled_text.configure(state='normal')
    AppUIComponents.send_button.config(state='normal')
    #hidding the AI Scribe button actions
    #toggle_button.config(state='normal')
    AppUIComponents.upload_button.config(state='normal')
    AppUIComponents.timestamp_listbox.config(state='normal')
    AppUIComponents.clear_button.config(state='normal')
    AppUIComponents.mic_test.set_mic_test_state(True)


def clear_all_text_fields():
    """Clears and resets all text fields in the application UI.

    Performs the following:
        - Clears user input field
        - Resets focus
        - Stops any flashing effects
        - Resets response display with default text
    """
    # Enable and clear user input field
    AppUIComponents.user_input.scrolled_text.configure(state='normal')
    AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)

    # Reset focus to main window
    AppUIComponents.user_input.scrolled_text.focus_set()
    AppContext.root.focus_set()

    stop_flashing()  # Stop any UI flashing effects

    # Reset response display with default text
    AppUIComponents.response_display.scrolled_text.configure(state='normal')
    AppUIComponents.response_display.scrolled_text.delete("1.0", tk.END)
    AppUIComponents.response_display.scrolled_text.insert(tk.END, "Medical Note")
    AppUIComponents.response_display.scrolled_text.config(fg='grey')
    AppUIComponents.response_display.scrolled_text.configure(state='disabled')


def display_text(text):
    AppUIComponents.response_display.scrolled_text.configure(state='normal')
    AppUIComponents.response_display.scrolled_text.delete("1.0", tk.END)
    AppUIComponents.response_display.scrolled_text.insert(tk.END, f"{text}\n")
    AppUIComponents.response_display.scrolled_text.configure(fg='black')
    AppUIComponents.response_display.scrolled_text.configure(state='disabled')


def update_gui_with_response(response_text):
    # nonlocal response_history, user_message, IS_FIRST_LOG

    if AppContext.IS_FIRST_LOG:
        AppUIComponents.timestamp_listbox.delete(0, tk.END)
        AppUIComponents.timestamp_listbox.config(fg='black')
        AppContext.IS_FIRST_LOG = False

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    AppContext.response_history.insert(0, (timestamp, AppContext.user_message, response_text))

    # Update the timestamp listbox
    AppUIComponents.timestamp_listbox.delete(0, tk.END)
    for time, _, _ in AppContext.response_history:
        AppUIComponents.timestamp_listbox.insert(tk.END, time)

    display_text(response_text)
    pyperclip.copy(response_text)
    stop_flashing()


def show_response(event):
    # nonlocal IS_FIRST_LOG

    if AppContext.IS_FIRST_LOG:
        return

    selection = event.widget.curselection()
    if selection:
        index = selection[0]
        transcript_text = AppContext.response_history[index][1]
        response_text = AppContext.response_history[index][2]
        AppUIComponents.user_input.scrolled_text.configure(state='normal')
        AppUIComponents.user_input.scrolled_text.config(fg='black')
        AppUIComponents.user_input.scrolled_text.delete("1.0", tk.END)
        AppUIComponents.user_input.scrolled_text.insert(tk.END, transcript_text)
        AppUIComponents.response_display.scrolled_text.configure(state='normal')
        AppUIComponents.response_display.scrolled_text.delete('1.0', tk.END)
        AppUIComponents.response_display.scrolled_text.insert('1.0', response_text)
        AppUIComponents.response_display.scrolled_text.config(fg='black')
        AppUIComponents.response_display.scrolled_text.configure(state='disabled')
        pyperclip.copy(response_text)


def display_screening_popup():
    """
    Display a popup window to inform the user of invalid input and offer options.

    :return: A boolean indicating the user's choice:
             - False if the user clicks 'Cancel'.
             - True if the user clicks 'Process Anyway!'.
    """
    # Create and display the popup window
    popup_result = PopupBox(
        parent=AppContext.root,
        title="Invalid Input",
        message=(
            "Input has been flagged as invalid. Please ensure the input is a conversation with more than "
            "50 words between a doctor and a patient. Unexpected results may occur from the AI."
        ),
        button_text_1="Cancel",
        button_text_2="Process Anyway!"
    )

    # Return based on the button the user clicks
    if popup_result.response == "button_1":
        return False
    elif popup_result.response == "button_2":
        return True


def start_flashing():
    AppContext.is_flashing = True
    flash_circle()


def stop_flashing():
    AppContext.is_flashing = False
    AppUIComponents.blinking_circle_canvas.itemconfig(AppUIComponents.circle, fill='white')  # Reset to default color


def flash_circle():
    if AppContext.is_flashing:
        current_color = AppUIComponents.blinking_circle_canvas.itemcget(AppUIComponents.circle, 'fill')
        new_color = 'blue' if current_color != 'blue' else 'black'
        AppUIComponents.blinking_circle_canvas.itemconfig(AppUIComponents.circle, fill=new_color)
        AppContext.root.after(1000, flash_circle)  # Adjust the flashing speed as needed


def toggle_view():
    """
    Toggles the user interface between a full view and a minimal view.

    Full view includes all UI components, while minimal view limits the interface
    to essential controls, reducing screen space usage. The function also manages
    window properties, button states, and binds/unbinds hover events for transparency.
    """

    if AppContext.current_view == "full":  # Transition to minimal view
        set_minimal_view()

    else:  # Transition back to full view
        set_full_view()


def set_full_view():
    """
    Configures the application to display the full view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Show all hidden UI components.
    - Reset window attributes such as size, transparency, and 'always on top' behavior.
    - Create the Docker status bar.
    - Restore the last known full view geometry if available.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_minimal_position: Saves the geometry of the window when switching from minimal view.
    """
    # Reset button sizes and placements for full view
    AppUIComponents.mic_button.config(width=11, height=2)
    AppUIComponents.pause_button.config(width=11, height=2)
    AppUIComponents.switch_view_button.config(width=11, height=2, text="Minimize View")

    # Show all UI components
    AppUIComponents.user_input.grid()
    AppUIComponents.send_button.grid()
    AppUIComponents.clear_button.grid()
    # AppUIComponents.toggle_button.grid()
    AppUIComponents.upload_button.grid()
    AppUIComponents.response_display.grid()
    AppUIComponents.history_frame.grid()
    AppUIComponents.mic_button.grid(row=1, column=1, pady=5, padx=0,sticky='nsew')
    AppUIComponents.pause_button.grid(row=1, column=2, pady=5, padx=0,sticky='nsew')
    AppUIComponents.switch_view_button.grid(row=1, column=6, pady=5, padx=0,sticky='nsew')
    AppUIComponents.blinking_circle_canvas.grid(row=1, column=7, padx=0,pady=5)
    AppUIComponents.footer_frame.grid()



    AppContext.window.toggle_menu_bar(enable=True, is_recording=AppContext.is_recording)

    # Reconfigure button styles and text
    AppUIComponents.mic_button.config(bg="red" if AppContext.is_recording else AppConstants.DEFAULT_BUTTON_COLOUR,
                      text="Stop\nRecording" if AppContext.is_recording else "Start\nRecording")
    AppUIComponents.pause_button.config(bg="red" if AppContext.is_paused else AppConstants.DEFAULT_BUTTON_COLOUR,
                        text="Resume" if AppContext.is_paused else "Pause")

    # Unbind transparency events and reset window properties
    AppContext.root.unbind('<Enter>')
    AppContext.root.unbind('<Leave>')
    AppContext.root.attributes('-alpha', 1.0)
    AppContext.root.attributes('-topmost', False)
    AppContext.root.minsize(900, 400)
    AppContext.current_view = "full"

    #Recreates Silence Warning Bar
    AppContext.window.destroy_warning_bar()
    check_silence_warning(silence_duration=AppContext.silent_warning_duration)

    # add the minimal view geometry and remove the last full view geometry
    add_min_max(AppContext.root)

    # create docker_status bar if enabled
    if AppContext.app_settings.editable_settings["Use Docker Status Bar"]:
        AppContext.window.create_docker_status_bar()

    if AppContext.app_settings.editable_settings["Enable Scribe Template"]:
        AppContext.window.destroy_scribe_template()
        AppContext.window.create_scribe_template()

    # Save minimal view geometry and restore last full view geometry
    AppContext.last_minimal_position = AppContext.root.geometry()
    AppContext.root.update_idletasks()
    if AppContext.last_full_position:
        AppContext.root.geometry(AppContext.last_full_position)
    else:
        AppContext.root.geometry("900x400")

    # Disable to make the window an app(show taskbar icon)
    # root.attributes('-toolwindow', False)


def set_minimal_view():

    """
    Configures the application to display the minimal view interface.

    Actions performed:
    - Reconfigure button dimensions and text.
    - Hide non-essential UI components.
    - Bind transparency hover events for better focus.
    - Adjust window attributes such as size, transparency, and 'always on top' behavior.
    - Destroy and optionally recreate specific components like the Scribe template.

    Global Variables:
    - current_view: Tracks the current interface state ('full' or 'minimal').
    - last_full_position: Saves the geometry of the window when switching from full view.
    """
    # Remove all non-essential UI components
    AppUIComponents.user_input.grid_remove()
    AppUIComponents.send_button.grid_remove()
    AppUIComponents.clear_button.grid_remove()
    # AppUIComponents.toggle_button.grid_remove()
    AppUIComponents.upload_button.grid_remove()
    AppUIComponents.response_display.grid_remove()
    AppUIComponents.history_frame.grid_remove()
    AppUIComponents.blinking_circle_canvas.grid_remove()
    AppUIComponents.footer_frame.grid_remove()
    # Configure minimal view button sizes and placements
    AppUIComponents.mic_button.config(width=2, height=1)
    AppUIComponents.pause_button.config(width=2, height=1)
    AppUIComponents.switch_view_button.config(width=2, height=1)

    AppUIComponents.mic_button.grid(row=0, column=0, pady=2, padx=2)
    AppUIComponents.pause_button.grid(row=0, column=1, pady=2, padx=2)
    AppUIComponents.switch_view_button.grid(row=0, column=2, pady=2, padx=2)

    # Update button text based on recording and pause states
    AppUIComponents.mic_button.config(text="⏹️" if AppContext.is_recording else "🎤")
    AppUIComponents.pause_button.config(text="▶️" if AppContext.is_paused else "⏸️")
    AppUIComponents.switch_view_button.config(text="⬆️")  # Minimal view indicator

    AppUIComponents.blinking_circle_canvas.grid(row=0, column=3, pady=2, padx=2)

    AppContext.window.toggle_menu_bar(enable=False)

    # Update window properties for minimal view
    AppContext.root.attributes('-topmost', True)
    AppContext.root.minsize(125, 50)  # Smaller minimum size for minimal view
    AppContext.current_view = "minimal"

    if AppContext.root.wm_state() == 'zoomed':  # Check if window is maximized
        AppContext.root.wm_state('normal')       # Restore the window

    #Recreates Silence Warning Bar
    AppContext.window.destroy_warning_bar()
    check_silence_warning(silence_duration=AppContext.silent_warning_duration)

    # Set hover transparency events
    def on_enter(e):
        if e.widget == AppContext.root:  # Ensure the event is from the root window
            AppContext.root.attributes('-alpha', 1.0)

    def on_leave(e):
        if e.widget == AppContext.root:  # Ensure the event is from the root window
            AppContext.root.attributes('-alpha', 0.70)

    AppContext.root.bind('<Enter>', on_enter)
    AppContext.root.bind('<Leave>', on_leave)

    # Destroy and re-create components as needed
    AppContext.window.destroy_docker_status_bar()
    if AppContext.app_settings.editable_settings["Enable Scribe Template"]:
        AppContext.window.destroy_scribe_template()
        AppContext.window.create_scribe_template(row=1, column=0, columnspan=3, pady=5)

    # Remove the minimal view geometry and save the current full view geometry
    remove_min_max(AppContext.root)

    # Save full view geometry and restore last minimal view geometry
    AppContext.last_full_position = AppContext.root.geometry()
    if AppContext.last_minimal_position:
        AppContext.root.geometry(AppContext.last_minimal_position)
    else:
        AppContext.root.geometry("125x50")  # Set the window size to the minimal view size


def add_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Add placeholder text to a tkinter Text widget when it's empty.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to add placeholder text to.
        placeholder_text (str, optional): The placeholder text to display. Defaults to "Text box".
    """
    if text_widget.get("1.0", "end-1c") == "":
        text_widget.insert("1.0", placeholder_text)
        text_widget.config(fg='grey')


def remove_placeholder(event, text_widget, placeholder_text="Text box"):
    """
    Remove placeholder text from a tkinter Text widget when it gains focus.

    Args:
        event: The event that triggered this function.
        text_widget: The tkinter Text widget to remove placeholder text from.
        placeholder_text (str, optional): The placeholder text to remove. Defaults to "Text box".
    """
    if text_widget.get("1.0", "end-1c") == placeholder_text:
        text_widget.delete("1.0", "end")
        text_widget.config(fg='black')


def copy_text(widget):
    """
    Copy text content from a tkinter widget to the system clipboard.

    Args:
        widget: A tkinter Text widget containing the text to be copied.
    """
    text = widget.get("1.0", tk.END)
    pyperclip.copy(text)


def check_silence_warning(silence_duration):
    """Check if silence warning should be displayed."""

    # Check if we need to warn if silence is long than warn time
    if silence_duration >= AppConstants.SILENCE_WARNING_LENGTH and AppContext.window.warning_bar is None and not AppContext.is_paused:
        if AppContext.current_view == "full":
            AppContext.window.create_warning_bar(f"No audio input detected for {AppConstants.SILENCE_WARNING_LENGTH} seconds. Please check and ensure your microphone input device is working.", closeButton=False)
        elif AppContext.current_view == "minimal":
            AppContext.window.create_warning_bar(f"🔇No audio for {AppConstants.SILENCE_WARNING_LENGTH}s.", closeButton=False)
    elif silence_duration <= AppConstants.SILENCE_WARNING_LENGTH and AppContext.window.warning_bar is not None:
        # If the warning bar is displayed, remove it
        AppContext.window.destroy_warning_bar()

import atexit
import sys
import tkinter as tk
from tkinter import ttk

from Model import ModelManager, ModelStatus
from UI.ImageWindow import ImageWindow
from UI.SettingsConstant import SettingsKeys
from UI.Widgets.CustomTextBox import CustomTextBox
from UI.Widgets.MicrophoneTestFrame import MicrophoneTestFrame
from UI.Widgets.TimestampListbox import TimestampListbox
from client_modules.app_context import AppContext, AppConstants, AppUIComponents
from client_modules.audio_processing import on_closing, threaded_toggle_recording, toggle_pause, upload_file, \
    clear_application_press
from client_modules.transcription import load_stt_model, unload_stt_model
from client_modules.ui_handlers import confirm_exit_and_destroy, remove_placeholder, add_placeholder, \
    toggle_view, show_response
from client_modules.llm_integration import send_and_flash
from utils.file_utils import get_file_path
from utils.log_config import logger
from utils.utils import get_application_version


# wait for both whisper and llm to be loaded before unlocking the settings button
def await_models(timeout_length=60):
    """
    Waits until the necessary models (Whisper and LLM) are fully loaded.

    The function checks if local models are enabled based on application settings.
    If a remote model is used, the corresponding flag is set to True immediately,
    bypassing the wait. Otherwise, the function enters a loop that periodically
    checks for model readiness and prints status updates until both models are loaded.

    :return: None
    """
    #if we cancel this thread then break out of the loop
    if AppContext.cancel_await_thread.is_set():
        logger.info("*** Model loading cancelled. Enabling settings bar.")
        #reset the flag
        AppContext.cancel_await_thread.clear()
        #reset the settings bar
        AppContext.window.enable_settings_menu()
        #return so the .after() doesnt get called.
        return

    # if we are using remote whisper then we can assume it is loaded and dont wait
    whisper_loaded = (not AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value] or AppContext.stt_local_model)

    # if we are not using local llm then we can assume it is loaded and dont wait
    llm_loaded = (not AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value] or ModelManager.local_model)

    # if there was a error stop checking
    if ModelManager.local_model == ModelStatus.ERROR:
        #Error message is displayed else where
        llm_loaded = True

    # wait for both models to be loaded
    if not whisper_loaded or not llm_loaded:
        logger.info("Waiting for models to load...")

        # override the lock in case something else tried to edit
        AppContext.window.disable_settings_menu()

        AppContext.root.after(100, await_models)
    else:
        logger.info("*** Models loaded successfully on startup.")

        # if error null out the model
        if ModelManager.local_model == ModelStatus.ERROR:
            ModelManager.local_model = None

        AppContext.window.enable_settings_menu()


def main():
    logger.info(f"{ AppConstants.APP_NAME=} { AppConstants.APP_TASK_MANAGER_NAME=} {get_application_version()=}")
    if AppContext.app_manager.run():
        sys.exit(1)
    AppContext.root.title(AppConstants.APP_NAME)
    # Register the close_mutex function to be called on exit
    atexit.register(on_closing)
    # remind user notes will be gone after exiting
    AppContext.root.protocol("WM_DELETE_WINDOW", confirm_exit_and_destroy)
    AppContext.app_settings.set_main_window(AppContext.window)
    if AppContext.app_settings.editable_settings["Use Docker Status Bar"]:
        AppContext.window.create_docker_status_bar()
    # Configure grid weights for scalability
    AppContext.root.grid_columnconfigure(0, weight=1, minsize=10)
    AppContext.root.grid_columnconfigure(1, weight=1)
    AppContext.root.grid_columnconfigure(2, weight=1)
    AppContext.root.grid_columnconfigure(3, weight=1)
    AppContext.root.grid_columnconfigure(4, weight=1)
    AppContext.root.grid_columnconfigure(5, weight=1)
    AppContext.root.grid_columnconfigure(6, weight=1)
    AppContext.root.grid_columnconfigure(7, weight=1)
    AppContext.root.grid_columnconfigure(8, weight=1)
    AppContext.root.grid_columnconfigure(9, weight=1)
    AppContext.root.grid_columnconfigure(10, weight=1)
    AppContext.root.grid_columnconfigure(11, weight=1, minsize=10)
    AppContext.root.grid_rowconfigure(0, weight=1)
    AppContext.root.grid_rowconfigure(1, weight=0)
    AppContext.root.grid_rowconfigure(2, weight=1)
    AppContext.root.grid_rowconfigure(3, weight=0)
    AppContext.root.grid_rowconfigure(4, weight=0)
    AppContext.window.load_main_window()
    user_input = CustomTextBox(AppContext.root, height=12)
    AppUIComponents.user_input = user_input
    user_input.grid(row=0, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')
    # Insert placeholder text
    user_input.scrolled_text.insert("1.0", "Transcript of Conversation")
    user_input.scrolled_text.config(fg='grey')
    # Bind events to remove or add the placeholder with arguments
    user_input.scrolled_text.bind("<FocusIn>", lambda event: remove_placeholder(event, user_input.scrolled_text,
                                                                                "Transcript of Conversation"))
    user_input.scrolled_text.bind("<FocusOut>", lambda event: add_placeholder(event, user_input.scrolled_text,
                                                                              "Transcript of Conversation"))
    mic_button = tk.Button(AppContext.root, text="Start\nRecording", command=lambda: (threaded_toggle_recording()),
                           height=2, width=11)
    AppUIComponents.mic_button = mic_button
    mic_button.grid(row=1, column=1, pady=5, sticky='nsew')
    send_button = tk.Button(AppContext.root, text="Generate Note", command=send_and_flash, height=2, width=11)
    AppUIComponents.send_button = send_button
    send_button.grid(row=1, column=3, pady=5, sticky='nsew')
    pause_button = tk.Button(AppContext.root, text="Pause", command=toggle_pause, height=2, width=11)
    AppUIComponents.pause_button = pause_button
    pause_button.grid(row=1, column=2, pady=5, sticky='nsew')
    clear_button = tk.Button(AppContext.root, text="Clear", command=clear_application_press, height=2, width=11)
    AppUIComponents.clear_button = clear_button
    clear_button.grid(row=1, column=4, pady=5, sticky='nsew')
    # hidding the AI Scribe button
    # toggle_button = tk.Button(root, text="AI Scribe\nON", command=toggle_aiscribe, height=2, width=11)
    # AppUIComponents.toggle_button = toggle_button
    # toggle_button.grid(row=1, column=5, pady=5, sticky='nsew')
    upload_button = tk.Button(AppContext.root, text="Upload Audio\nFor Transcription", command=upload_file, height=2,
                              width=11)
    AppUIComponents.upload_button = upload_button
    upload_button.grid(row=1, column=5, pady=5, sticky='nsew')
    switch_view_button = tk.Button(AppContext.root, text="Minimize View", command=toggle_view, height=2, width=11)
    AppUIComponents.switch_view_button = switch_view_button
    switch_view_button.grid(row=1, column=6, pady=5, sticky='nsew')
    blinking_circle_canvas = tk.Canvas(AppContext.root, width=20, height=20)
    AppUIComponents.blinking_circle_canvas = blinking_circle_canvas
    blinking_circle_canvas.grid(row=1, column=7, pady=5)
    circle = blinking_circle_canvas.create_oval(5, 5, 15, 15, fill='white')
    AppUIComponents.circle = circle
    response_display = CustomTextBox(AppContext.root, height=13, state="disabled")
    AppUIComponents.response_display = response_display
    response_display.grid(row=2, column=1, columnspan=8, padx=5, pady=15, sticky='nsew')
    # Insert placeholder text
    response_display.scrolled_text.configure(state='normal')
    response_display.scrolled_text.insert("1.0", "Medical Note")
    response_display.scrolled_text.config(fg='grey')
    response_display.scrolled_text.configure(state='disabled')
    if AppContext.app_settings.editable_settings["Enable Scribe Template"]:
        AppContext.window.create_scribe_template()
    # Create a frame to hold both timestamp listbox and mic test
    history_frame = ttk.Frame(AppContext.root)
    AppUIComponents.history_frame = history_frame
    history_frame.grid(row=0, column=9, columnspan=2, rowspan=6, padx=5, pady=10, sticky='nsew')
    # Configure the frame's grid
    history_frame.grid_columnconfigure(0, weight=1)
    history_frame.grid_rowconfigure(0, weight=4)  # Timestamp takes more space
    history_frame.grid_rowconfigure(1, weight=1)
    history_frame.grid_rowconfigure(2, weight=1)  # Mic test takes less space
    history_frame.grid_rowconfigure(3, weight=1)
    system_font = tk.font.nametofont("TkDefaultFont")
    base_size = system_font.cget("size")
    scaled_size = int(base_size * 0.9)  # 90% of system font size
    # Add warning label
    warning_label = tk.Label(history_frame,
                             text="Temporary Note History will be cleared when app closes",
                             # fg="red",
                             # wraplength=200,
                             justify="left",
                             font=tk.font.Font(size=scaled_size),
                             )
    warning_label.grid(row=3, column=0, sticky='ew', pady=(0, 5))
    # Add the timestamp listbox
    timestamp_listbox = TimestampListbox(history_frame, height=30, exportselection=False,
                                         response_history=AppContext.response_history)
    AppUIComponents.timestamp_listbox = timestamp_listbox
    timestamp_listbox.grid(row=0, column=0, rowspan=3, sticky='nsew')
    timestamp_listbox.bind('<<ListboxSelect>>', show_response)
    timestamp_listbox.insert(tk.END, "Temporary Note History")
    timestamp_listbox.config(fg='grey')
    # Add microphone test frame
    mic_test = MicrophoneTestFrame(parent=history_frame, p=AppContext.p, app_settings=AppContext.app_settings,
                                   root=AppContext.root)
    AppUIComponents.mic_test = mic_test
    mic_test.frame.grid(row=4, column=0, pady=10, sticky='nsew')  # Use grid to place the frame
    # Add a footer frame at the bottom of the window
    footer_frame = tk.Frame(AppContext.root, bg="lightgray", height=30)
    AppUIComponents.footer_frame = footer_frame
    footer_frame.grid(row=100, column=0, columnspan=100, sticky="ew")  # Use grid instead of pack
    # Add "Version 2" label in the center of the footer
    version = get_application_version()
    version_label = tk.Label(footer_frame, text=f"FreeScribe Client {version}", bg="lightgray", fg="black").pack(
        side="left", expand=True, padx=2, pady=5)
    AppContext.window.update_aiscribe_texts(None)
    # Bind Alt+P to send_and_receive function
    AppContext.root.bind('<Alt-p>', lambda event: pause_button.invoke())
    # Bind Alt+R to toggle_recording function
    AppContext.root.bind('<Alt-r>', lambda event: mic_button.invoke())
    # set min size
    AppContext.root.minsize(900, 400)
    if (AppContext.app_settings.editable_settings['Show Welcome Message']):
        AppContext.window.show_welcome_message()
        ImageWindow(AppContext.root, "Help Guide", get_file_path('assets', 'help.png'))
    # Wait for the UI root to be intialized then load the model. If using local llm.
    if AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value]:
        def on_cancel_llm_load():
            AppContext.cancel_await_thread.set()

        AppContext.root.after(100, lambda: (
            ModelManager.setup_model(app_settings=AppContext.app_settings, root=AppContext.root,
                                     on_cancel=on_cancel_llm_load)))
    if AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_WHISPER.value]:
        # Inform the user that Local Whisper is being used for transcription
        logger.info("Using Local Whisper for transcription.")
        AppContext.root.after(100, lambda: (load_stt_model()))
    AppContext.root.after(100, await_models)
    AppContext.root.bind("<<LoadSttModel>>", load_stt_model)
    AppContext.root.bind("<<UnloadSttModel>>", unload_stt_model)
    AppContext.root.mainloop()
    AppContext.p.terminate()

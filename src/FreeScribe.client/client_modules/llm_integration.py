#hidding the AI Scribe button Function
# def toggle_aiscribe():
#     AppContext.use_aiscribe = not AppContext.use_aiscribe
#     toggle_button.config(text="AI Scribe\nON" if AppContext.use_aiscribe else "AI Scribe\nOFF")
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox as messagebox

import requests
import scrubadub

from Model import ModelManager
from UI.LoadingWindow import LoadingWindow
from UI.ScrubWindow import ScrubWindow
from UI.SettingsConstant import SettingsKeys
from client_modules.app_context import AppContext, AppUIComponents, AppConstants
from client_modules.tools import kill_thread
from client_modules.ui_handlers import update_gui_with_response, display_text, display_screening_popup, stop_flashing, \
    start_flashing
from services.factual_consistency import find_factual_inconsistency
from utils.ip_utils import is_private_ip
from utils.log_config import logger


def send_text_to_api(edited_text):
    headers = {
        "Authorization": f"Bearer {AppContext.app_settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {}

    try:
        payload = {
            "model": AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value].strip(),
            "messages": [
                {"role": "user", "content": edited_text}
            ],
            "temperature": float(AppContext.app_settings.editable_settings["temperature"]),
            "top_p": float(AppContext.app_settings.editable_settings["top_p"]),
            "top_k": int(AppContext.app_settings.editable_settings["top_k"]),
            "tfs": float(AppContext.app_settings.editable_settings["tfs"]),
        }

        if AppContext.app_settings.editable_settings["best_of"]:
            payload["best_of"] = int(AppContext.app_settings.editable_settings["best_of"])

    except ValueError as e:
        payload = {
            "model": AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM_MODEL.value].strip(),
            "messages": [
                {"role": "user", "content": edited_text}
            ],
            "temperature": 0.1,
            "top_p": 0.4,
            "top_k": 30,
            "best_of": 6,
            "tfs": 0.97,
        }

        if AppContext.app_settings.editable_settings["best_of"]:
            payload["best_of"] = int(AppContext.app_settings.editable_settings["best_of"])

        logger.info(f"Error parsing settings: {e}. Using default settings.")

    try:

        if AppContext.app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value].endswith('/'):
            AppContext.app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value] = AppContext.app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value][:-1]

        # Open API Style
        verify = not AppContext.app_settings.editable_settings["AI Server Self-Signed Certificates"]
        response = requests.post(
            AppContext.app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value] + "/chat/completions", headers=headers, json=payload, verify=verify)

        response.raise_for_status()
        response_data = response.json()
        response_text = (response_data['choices'][0]['message']['content'])
        return response_text

        #############################################################
        #                                                           #
        #                   OpenAI API Style                        #
        #           Uncomment to use API Style Selector             #
        #                                                           #
        #############################################################

        # if app_settings.API_STYLE == "OpenAI":
        # elif app_settings.API_STYLE == "KoboldCpp":
        #     prompt = get_prompt(edited_text)

        #     verify = not app_settings.editable_settings["AI Server Self-Signed Certificates"]
        #     response = requests.post(app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value] + "/api/v1/generate", json=prompt, verify=verify)

        #     if response.status_code == 200:
        #         results = response.json()['results']
        #         response_text = results[0]['text']
        #         response_text = response_text.replace("  ", " ").strip()
        #         return response_text

    except Exception as e:
        raise e


def send_text_to_localmodel(edited_text):
    # Send prompt to local model and get response
    if ModelManager.local_model is None:
        ModelManager.setup_model(app_settings=AppContext.app_settings, root=AppContext.root)

        timer = 0
        while ModelManager.local_model is None and timer < 30:
            timer += 0.1
            time.sleep(0.1)


    return ModelManager.local_model.generate_response(
        edited_text,
        temperature=float(AppContext.app_settings.editable_settings["temperature"]),
        top_p=float(AppContext.app_settings.editable_settings["top_p"]),
        repeat_penalty=float(AppContext.app_settings.editable_settings["rep_pen"]),
    )


def screen_input_with_llm(conversation):
    """
    Send a conversation to a large language model (LLM) for prescreening.
    :param conversation: A string containing the conversation to be screened.
    :return: A boolean indicating whether the conversation is valid.
    """
    # Define the chunk size (number of words per chunk)
    words_per_chunk = 60  # Adjust this value based on your results
    # Split the conversation into words
    words = conversation.split()
    # Split the words into chunks
    chunks = [' '.join(words[i:i + words_per_chunk]) for i in range(0, len(words), words_per_chunk)]
    logger.info(f"Total chunks count: {len(chunks)}")
    return any(process_chunk(chunk) for chunk in chunks)


def process_chunk(chunk):
    """
    Process a chunk of the conversation using the LLM.
    """
    prompt = (
        "Analyze the following conversation and determine if it is a valid doctor-patient conversation. "
        "A valid conversation involves a discussion between a healthcare provider and a patient about medical concerns, "
        "symptoms, diagnoses, treatments, or health management. It may include:\n"
        "- Descriptions of symptoms or health issues.\n"
        "- Discussions about medications, treatments, or follow-up plans.\n"
        "- Questions and answers related to the patient's health.\n"
        "- Casual or conversational tones, as long as the topic is medically relevant.\n\n"
        "If the conversation is unrelated to healthcare, lacks medical context, or appears to be non-medical, "
        "it is not a valid doctor-patient conversation.\n\n"
        "Return only one word: 'True' if the conversation is valid, or 'False' if it is not. "
        "Do not provide explanations, additional formatting, or any text other than 'True' or 'False'.\n\n"
        "Here is the conversation:\n"
    )
    # Send the prompt and chunk to the LLM for evaluation
    prescreen = send_text_to_chatgpt(f"{prompt}{chunk}")
    # Check if the response from the LLM is 'true' (case-insensitive)
    return prescreen.strip().lower() == "true"


def has_more_than_50_words(text: str) -> bool:
    # Split the text into words using whitespace as the delimiter
    words = text.split()
    # Print the number of words
    logger.info(f"Number of words: {len(words)}")
    # Check if the number of words is greater than 50
    return len(words) > 50


def screen_input(user_input_msg):
    """
    Screen the user's input message based on the application's settings.

    :param user_input_msg: The message to be screened.
    :return: A boolean indicating whether the input is valid and accepted for further processing.
    """
    validators = []
    if AppContext.app_settings.editable_settings[SettingsKeys.Enable_Word_Count_Validation.value]:
        validators.append(has_more_than_50_words)

    if AppContext.app_settings.editable_settings[SettingsKeys.Enable_AI_Conversation_Validation.value]:
        validators.append(screen_input_with_llm)

    return all(validator(user_input_msg) for validator in validators)


def threaded_screen_input(user_input_msg, screen_return):
    """
    Screen the user's input message based on the application's settings in a separate thread.

    :param user_input_msg: The message to be screened.
    :param screen_return: A boolean variable to store the result of the screening.
    """
    input_return = screen_input(user_input_msg)
    screen_return.set(input_return)


def send_text_to_chatgpt(edited_text):
    if AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value]:
        return send_text_to_localmodel(edited_text)
    else:
        return send_text_to_api(edited_text)


def generate_note(formatted_message):
    """Generate a note from the formatted message.

    This function processes the input text and generates a medical note or AI response
    based on application settings. It supports pre-processing, post-processing, and
    factual consistency verification.

    :param formatted_message: The transcribed conversation text to generate a note from
    :type formatted_message: str

    :returns: True if note generation was successful, False otherwise
    :rtype: bool

    .. note::
        The behavior of this function depends on several application settings:
        - If 'use_aiscribe' is True, it generates a structured medical note
        - If 'Use Pre-Processing' is enabled, it first generates a list of facts
        - If 'Use Post-Processing' is enabled, it refines the generated note
        - Factual consistency verification is performed on the final note
    """
    try:
        summary = None
        if AppContext.use_aiscribe:
            # If pre-processing is enabled
            if AppContext.app_settings.editable_settings["Use Pre-Processing"]:
                #Generate Facts List
                list_of_facts = send_text_to_chatgpt(f"{AppContext.app_settings.editable_settings['Pre-Processing']} {formatted_message}")

                #Make a note from the facts
                medical_note = send_text_to_chatgpt(f"{AppContext.app_settings.AISCRIBE} {list_of_facts} {AppContext.app_settings.AISCRIBE2}")

                # If post-processing is enabled check the note over
                if AppContext.app_settings.editable_settings["Use Post-Processing"]:
                    post_processed_note = send_text_to_chatgpt(f"{AppContext.app_settings.editable_settings['Post-Processing']}\nFacts:{list_of_facts}\nNotes:{medical_note}")
                    update_gui_with_response(post_processed_note)
                    summary = post_processed_note
                else:
                    update_gui_with_response(medical_note)
                    summary = medical_note

            else: # If pre-processing is not enabled then just generate the note
                medical_note = send_text_to_chatgpt(f"{AppContext.app_settings.AISCRIBE} {formatted_message} {AppContext.app_settings.AISCRIBE2}")

                if AppContext.app_settings.editable_settings["Use Post-Processing"]:
                    post_processed_note = send_text_to_chatgpt(f"{AppContext.app_settings.editable_settings['Post-Processing']}\nNotes:{medical_note}")
                    update_gui_with_response(post_processed_note)
                    summary = post_processed_note
                else:
                    update_gui_with_response(medical_note)
                    summary = medical_note
        else: # do not generate note just send text directly to AI
            ai_response = send_text_to_chatgpt(formatted_message)
            update_gui_with_response(ai_response)
            summary = ai_response
        check_and_warn_about_factual_consistency(formatted_message, summary)

        return True
    except Exception as e:
        #TODO: Implement proper logging to system event logger
        logger.error(f"An error occurred: {e}")
        display_text(f"An error occurred: {e}")
        return False


def check_and_warn_about_factual_consistency(formatted_message: str, medical_note: str) -> None:
    """Verify and warn about potential factual inconsistencies in generated medical notes.

    This function checks the consistency between the original conversation and the generated
    medical note using multiple verification methods. If inconsistencies are found, a warning
    dialog is shown to the user.

    :param formatted_message: The original transcribed conversation text
    :type formatted_message: str
    :param medical_note: The generated medical note to verify
    :type medical_note: str
    :returns: None

    .. note::
        The verification is only performed if factual consistency checking is enabled
        in the application settings.

    .. warning::
        Even if no inconsistencies are found, this does not guarantee the note is 100% accurate.
        Always review generated notes carefully.
    """
    # Verify factual consistency
    if not AppContext.app_settings.editable_settings[SettingsKeys.FACTUAL_CONSISTENCY_VERIFICATION.value]:
        return

    inconsistent_entities = find_factual_inconsistency(formatted_message, medical_note)
    logger.info(f"Inconsistent entities: {inconsistent_entities}")

    if inconsistent_entities:
        entities = '\n'.join(f'- {entity}' for entity in inconsistent_entities)
        warning_message = (
            "Heads-up: Potential inconsistencies detected in the generated note:\n\n"
            "Entities not in original conversation found:\n"
            f"{entities}"
            "\n\nPlease review the note for accuracy."
        )
        messagebox.showwarning("Factual Consistency Heads-up", warning_message)


def generate_note_thread(text: str):
    """
    Generate a note from the given text and update the GUI with the response.

    :param text: The text to generate a note from.
    :type text: str
    """

    AppContext.generation_thread_id = None

    def cancel_note_generation(thread_id, screen_thread):
        """Cancels any ongoing note generation.

        Sets the global flag to stop note generation operations.
        """

        try:
            if thread_id:
                kill_thread(thread_id)

            # check if screen thread is active before killing it
            if screen_thread and screen_thread.is_alive():
                kill_thread(screen_thread.ident)
        except Exception as e:
            # Log the error message
            # TODO implment system logger
            logger.error(f"An error occurred: {e}")
        finally:
            AppContext.generation_thread_id = None
            stop_flashing()

    # Track the screen input thread
    screen_thread = None
    # The return value from the screen input thread
    screen_return = tk.BooleanVar()

    loading_window = LoadingWindow(AppContext.root, "Screening Input Text", "Ensuring input is valid. Please wait.", on_cancel=lambda: (cancel_note_generation(
        AppContext.generation_thread_id, screen_thread)))
    # screen input in its own thread so we can cancel it
    screen_thread = threading.Thread(target=threaded_screen_input, args=(text, screen_return))
    screen_thread.start()
    #wait for the thread to join/cancel so we can continue
    screen_thread.join()

    # Check if the screen input was canceled or force overridden by the user
    if screen_return.get() is False:
        loading_window.destroy()

        # display the popup
        if display_screening_popup() is False:
            return

    loading_window.destroy()
    loading_window = LoadingWindow(AppContext.root, "Generating Note.", "Generating Note. Please wait.", on_cancel=lambda: (cancel_note_generation(
        AppContext.generation_thread_id, screen_thread)))


    thread = threading.Thread(target=generate_note, args=(text,))
    thread.start()
    AppContext.generation_thread_id = thread.ident

    def check_thread_status(thread, loading_window):
        if thread.is_alive():
            AppContext.root.after(500, lambda: check_thread_status(thread, loading_window))
        else:
            loading_window.destroy()
            stop_flashing()

    AppContext.root.after(500, lambda: check_thread_status(thread, loading_window))


def send_and_receive():
    AppContext.user_message = AppUIComponents.user_input.scrolled_text.get("1.0", tk.END).strip()
    display_text(AppConstants.NOTE_CREATION)
    threaded_handle_message(AppContext.user_message)


def threaded_handle_message(formatted_message):
    thread = threading.Thread(target=show_edit_transcription_popup, args=(formatted_message,))
    thread.start()
    return thread


def send_and_flash():
    start_flashing()
    send_and_receive()


def show_edit_transcription_popup(formatted_message):
    scrubber = scrubadub.Scrubber()

    scrubbed_message = scrubadub.clean(formatted_message)

    pattern = r'\b\d{10}\b'     # Any 10 digit number, looks like OHIP
    cleaned_message = re.sub(pattern,'{{OHIP}}',scrubbed_message)

    if (AppContext.app_settings.editable_settings[SettingsKeys.LOCAL_LLM.value] or is_private_ip(
            AppContext.app_settings.editable_settings[SettingsKeys.LLM_ENDPOINT.value])) and not AppContext.app_settings.editable_settings["Show Scrub PHI"]:
        generate_note_thread(cleaned_message)
        return

    def on_proceed(edited_text):
        thread = threading.Thread(target=generate_note_thread, args=(edited_text,))
        thread.start()

    def on_cancel():
        stop_flashing()

    ScrubWindow(AppContext.root, cleaned_message, on_proceed, on_cancel)

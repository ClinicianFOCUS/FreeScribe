"""
Recordings Manager UI for FreeScribe client application
"""

import os
import wave
import io
import threading
import tkinter as tk
import pyaudio
import audioop
import requests
import numpy as np
from tkinter import Toplevel, Listbox, Button, Frame, messagebox, ttk, Label
from tkinter import filedialog
from utils.file_utils import get_resource_path
import utils.AESCryptoUtils as AESCryptoUtils
import utils.audio
from UI.SettingsConstant import SettingsKeys
from UI.LoadingWindow import LoadingWindow
from utils.log_config import logger

class RecordingsManager:
    
    last_selected_data = None

    def __init__(self, parent):
        self.parent = parent
        self.popup = Toplevel(parent)
        self.popup.title("Manage Recordings")
        self.popup.geometry("650x450")

        self.p_audio = pyaudio.PyAudio()
        self.stream = None
        self.current_position = 0
        self.is_playing = False
        self.is_paused = False
        self.current_file = None
        self.wf = None
        self.wf_buffer = None
        self.volume_level = 1.0

        self.setup_ui()
        self.popup.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Initialize all UI components"""
        # Recordings list frame
        recordings_frame = Frame(self.popup)
        recordings_frame.pack(fill='both', expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(recordings_frame)
        scrollbar.pack(side='right', fill='y')

        self.recordings_list = Listbox(recordings_frame, yscrollcommand=scrollbar.set)
        self.recordings_list.pack(fill='both', expand=True)
        scrollbar.config(command=self.recordings_list.yview)

        # Populate recordings list
        if os.path.exists(get_resource_path("recordings")):
            recordings_dir = get_resource_path("recordings")
            files_found = False
            for f in sorted(os.listdir(recordings_dir)):
                if f.endswith('.AE2'):
                    self.recordings_list.insert('end', f)
                    files_found = True
            
            if not files_found:
                self.recordings_list.insert('end', "No recordings found")
                self.recordings_list.itemconfig(0, {'fg': 'gray'})
        else:
            self.recordings_list.insert('end', "No recordings found")
            self.recordings_list.itemconfig(0, {'fg': 'gray'})

        # Playback controls
        controls_frame = Frame(self.popup)
        controls_frame.pack(fill='x', padx=10, pady=5)

        self.position_var = tk.DoubleVar(value=0)
        self.duration_var = tk.DoubleVar(value=0)

        self.position_scale = ttk.Scale(
            controls_frame,
            from_=0,
            to=100,
            variable=self.position_var,
            command=self.seek_position,
            length=300
        )
        self.position_scale.pack(side='left', expand=True, fill='x', padx=5)

        self.time_label = Label(controls_frame, text="00:00 / 00:00")
        self.time_label.pack(side='left', padx=5)

        # Action buttons
        buttons_frame = Frame(self.popup)
        buttons_frame.pack(fill='x', padx=10, pady=5)

        self.play_button = Button(buttons_frame, text="▶️", command=self.toggle_playback, width=5)
        self.play_button.pack(side='left', padx=5)

        self.delete_button = Button(buttons_frame, text="🗑️ Delete", command=self.delete_recording)
        self.delete_button.pack(side='left', padx=5)

        self.save_button = Button(buttons_frame, text="💾 Save Unencrypted", command=self.save_unencrypted)
        self.save_button.pack(side='left', padx=5)

        self.generate_button = Button(buttons_frame, text="📝 Generate Note", command=self.generate_note)
        self.generate_button.pack(side='left', padx=5)

        self.close_button = Button(buttons_frame, text="Close", command=self.on_close)
        self.close_button.pack(side='right', padx=5)

        # Start position updates
        self.update_time_label()

    def update_position(self):
        """Update playback position indicator"""
        if self.is_playing and not self.is_paused and self.stream and self.stream.is_active():
            self.position_var.set(self.current_position)
            self.position_scale.set(self.current_position)
        self.popup.after(200, self.update_position)

    def play_selected(self):
        """Play the selected recording"""
        selection = self.recordings_list.curselection()
        if not selection:
            return

        filename = self.recordings_list.get(selection[0])

        try:
            self.stop_playback()

            encrypted_path = get_resource_path(f"recordings/{filename}")
            with open(encrypted_path, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = AESCryptoUtils.AESCryptoUtilsClass.decrypt_bytes(encrypted_data)

            self.wf_buffer = io.BytesIO(decrypted_data)
            self.wf = wave.open(self.wf_buffer, 'rb')
            self.duration_var.set(self.wf.getnframes() / self.wf.getframerate())
            self.position_var.set(0)
            self.position_scale.config(to=self.duration_var.get())

            self.stream = self.p_audio.open(
                format=self.p_audio.get_format_from_width(self.wf.getsampwidth()),
                channels=self.wf.getnchannels(),
                rate=self.wf.getframerate(),
                output=True,
                frames_per_buffer=1024
            )

            self.is_playing = True
            self.is_paused = False
            self.current_file = filename
            self.current_position = 0
            self.play_button.config(text="⏸️")

            threading.Thread(target=self.play_audio, daemon=True).start()
            self.update_position()

        except Exception as e:
            logger.exception("Error playing recording")
            messagebox.showerror("Error", f"Could not play recording: {str(e)}")

    def play_audio(self):
        """Audio playback thread"""
        try:
            self.wf.setpos(int(self.current_position * self.wf.getframerate()))
            chunk_size = 1024

            while self.is_playing:
                if self.is_paused:
                    continue

                data = self.wf.readframes(chunk_size)
                if not data:
                    break

                if self.volume_level < 1.0:
                    data = audioop.mul(data, self.wf.getsampwidth(), self.volume_level)

                self.stream.write(data)

                frames_written = len(data) // (self.wf.getsampwidth() * self.wf.getnchannels())
                self.current_position += frames_written / self.wf.getframerate()

        except Exception as e:
            logger.exception("Playback error")
            messagebox.showerror("Playback Error", f"Error during playback: {str(e)}")
        finally:
            self.stop_playback()

    def toggle_playback(self):
        """Toggle play/pause state"""
        if not self.is_playing:
            self.play_selected()
        else:
            self.is_paused = not self.is_paused
            self.play_button.config(text="▶️" if self.is_paused else "⏸️")

    def stop_playback(self):
        """Stop current playback and clean up resources"""
        self.is_playing = False
        self.is_paused = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.wf:
            self.wf.close()
            self.wf = None
        if self.wf_buffer:
            self.wf_buffer.close()
            self.wf_buffer = None
        self.play_button.config(text="▶️")

    def seek_position(self, pos):
        """Seek to specific position in recording"""
        self.current_position = float(pos)
        self.position_var.set(self.current_position)
        if self.is_playing and not self.is_paused and self.wf:
            self.wf.setpos(int(self.current_position * self.wf.getframerate()))

    def delete_recording(self):
        """Delete selected recording"""
        selection = self.recordings_list.curselection()
        if not selection:
            return

        filename = self.recordings_list.get(selection[0])
        encrypted_path = get_resource_path(f"recordings/{filename}")
        decrypted_path = encrypted_path.replace('.AE2', '.wav')

        try:
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)
            if os.path.exists(decrypted_path):
                os.remove(decrypted_path)
            self.recordings_list.delete(selection[0])
        except Exception as e:
            logger.exception("Error deleting recording")
            messagebox.showerror("Error", f"Could not delete recording: {str(e)}")

    def save_unencrypted(self):
        """Save decrypted version of recording"""
        selection = self.recordings_list.curselection()
        if not selection:
            return

        filename = self.recordings_list.get(selection[0])
        decrypted_file = filename

        if save_path := filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("WAV files", "*.wav")],
            initialfile=f"{decrypted_file}.wav"
        ):
            try:
                decrypted_file_data = utils.audio.decrypt_whole_audio_file(decrypted_file)

                # Basic WAV parameters
                sample_rate = 16000  # Adjust as needed
                n_channels = 1       # Mono
                
                # Ensure data is in 16-bit integer format
                audio_data = decrypted_file_data.astype(np.int16)
                
                # Write WAV file
                with open(save_path, 'wb') as f:
                    wav = wave.open(f, 'wb')
                    wav.setnchannels(n_channels)
                    wav.setsampwidth(2)  # 2 bytes for 16-bit
                    wav.setframerate(sample_rate)
                    wav.writeframes(audio_data.tobytes())
                    wav.close()
            except Exception as e:
                logger.exception("Error saving recording")
                messagebox.showerror("Error", f"Could not save recording: {str(e)}")
                logger.exception("Error saving recording")

    def update_time_label(self):
        """Update time display label"""
        current_time = self.position_var.get()
        duration = self.duration_var.get()
        self.time_label.config(text=f"{self.format_time(current_time)} / {self.format_time(duration)}")
        self.popup.after(200, self.update_time_label)

    def format_time(self, seconds):
        """Format seconds into MM:SS"""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def generate_note(self):
        """Generate a note from the selected recording"""
        def note_loading():
            
            selection = self.recordings_list.curselection()
            if not selection:
                return
            
            # Note: The path is gotten in decrypt_whole_audio_file method
            filename = self.recordings_list.get(selection[0])
            encrypted_path = filename

            try:
                # Decrypt and get transcription
                wav_data = utils.audio.decrypt_whole_audio_file(encrypted_path)

                RecordingsManager.last_selected_data = wav_data
                self.parent.event_generate("<<GenerateNote>>")
                
                self.popup.destroy()
                
            except Exception as e:
                logger.exception("Error generating note")
                messagebox.showerror("Error", f"Could not generate note: {str(e)}")

        self.parent.after(0, note_loading)


    def on_close(self):
        """Clean up resources when window closes"""
        self.stop_playback()
        self.p_audio.terminate()
        self.popup.destroy()

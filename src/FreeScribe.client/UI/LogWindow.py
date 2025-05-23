import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from utils.AESCryptoUtils import AESCryptoUtilsClass
from utils.file_utils import get_resource_path
import threading
from UI.LoadingWindow import LoadingWindow
from utils.log_config import logger
import base64

class LogWindow:
    def __init__(self, parent_root):
        self.root = tk.Toplevel(parent_root)
        self.root.title("Encrypted Log Viewer")
        
        # Make window stay on top and grab focus
        self.root.attributes('-topmost', True)
        self.root.focus_force()
        self.root.grab_set()

        self.text_widget = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=100, height=40)
        self.text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=(0, 10))

        tk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save to Disk", command=self.save_to_disk).pack(side=tk.LEFT, padx=5)

        self.load_log()

    def load_log(self):
        loading = LoadingWindow(self.root,
                                title="Loading Log",
                                initial_text="Decrypting log file…",
                                note_text="May take a moment.")

        def on_done(result=None, error=None):
            loading.destroy()
            if error:
                messagebox.showerror("Error", f"Failed to load log:\n{error}", parent=self.root)
            else:
                self._update_text_widget(result)

        self._start_decrypt_thread(on_done)

    def _start_decrypt_thread(self, callback):
        def target():
            try:
                lines = self._decrypt_file()
                self.root.after(0, lambda: callback(result=lines))
            except Exception as e:
                self.root.after(0, lambda: callback(error=e))

        t = threading.Thread(target=target, daemon=True)
        t.start()

    def _decrypt_file(self):
        path = get_resource_path("freescribe.log")
        with open(path, "r") as f:
            raw = f.read().splitlines()

        out = []
        for enc in raw:
            if not enc:
                continue
            try:
                out.append(AESCryptoUtilsClass.decrypt(enc) + "\n")
            except Exception as ex:
                out.append(f"[Failed to decrypt line]: {ex}\n")
        return out

    def _update_text_widget(self, lines):
        #check if text widget is  exist
        if self.text_widget.winfo_exists():
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert(tk.END, "".join(lines))
            
    def copy_to_clipboard(self):
        content = self.text_widget.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    def save_to_disk(self):
        confirm = messagebox.askyesno(
            "Warning: Potential PHI Leak",
            "Saving decrypted logs to disk may leak Protected Health Information (PHI).\n\nAre you sure you want to proceed?",
            parent=self.root,
        )
        if not confirm:
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], parent=self.root)
        if file_path:
            try:
                content = self.text_widget.get(1.0, tk.END).strip()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Saved", f"File saved to:\n{file_path}")
            except Exception as e:
                logger.exception("Failed to save file")
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
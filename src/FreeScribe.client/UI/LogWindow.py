import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from utils.AESCryptoUtils import AESCryptoUtilsClass
from utils.file_utils import get_resource_path
import base64

class LogWindow:
    def __init__(self, parent_root):
        self.root = tk.Toplevel(parent_root)
        self.root.title("Encrypted Log Viewer")

        self.text_widget = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, width=100, height=40)
        self.text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=(0, 10))

        tk.Button(button_frame, text="Copy to Clipboard", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Save to Disk", command=self.save_to_disk).pack(side=tk.LEFT, padx=5)

        self.load_log()

    def load_log(self):
        file_path = get_resource_path("freescribe.log")
        try:
            with open(file_path, "r") as f:
                encrypted_lines = f.readlines()

            self.text_widget.delete(1.0, tk.END)
            for enc_line in encrypted_lines:
                enc_line = enc_line.strip()
                if not enc_line:
                    continue
                try:
                    decrypted_text = AESCryptoUtilsClass.decrypt(enc_line)
                    self.text_widget.insert(tk.END, decrypted_text + "\n")
                except Exception as line_err:
                    self.text_widget.insert(tk.END, f"[Failed to decrypt line]: {line_err}\n")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load or decrypt log:\n{str(e)}")

    def copy_to_clipboard(self):
        content = self.text_widget.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)

    def save_to_disk(self):
        confirm = messagebox.askyesno(
            "Warning: Potential PHI Leak",
            "Saving decrypted logs to disk may leak Protected Health Information (PHI).\n\nAre you sure you want to proceed?"
        )
        if not confirm:
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                content = self.text_widget.get(1.0, tk.END).strip()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                messagebox.showinfo("Saved", f"File saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")
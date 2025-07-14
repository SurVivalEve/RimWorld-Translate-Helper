import os
import opencc
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

# Available OpenCC Conversion Modes
opencc_modes = {
    "Simplified → Traditional (General)": "s2t.json",
    "Traditional → Simplified": "t2s.json",
    "Simplified → Traditional (Taiwan)": "s2tw.json",
    "Traditional (Taiwan) → Simplified": "tw2s.json",
    "Simplified → Traditional (Hong Kong)": "s2hk.json",
    "Traditional (Hong Kong) → Simplified": "hk2s.json",
    "Simplified → Traditional (Taiwan, with variants)": "s2twp.json",
    "Traditional (Taiwan, with variants) → Simplified": "tw2sp.json",
}

# Default Steam Workshop Path
default_steam_folder = r"D:\SteamLibrary\steamapps\workshop\content"

# Output Folder Options
output_language_options = ["ChineseTraditional", "ChineseSimplified", "Manual"]

def log_message(message):
    """Logs messages in the UI."""
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)

def select_input_folder():
    """Select input folder and auto-set output folder if not manually changed."""
    folder = filedialog.askdirectory(initialdir=default_steam_folder)
    if folder:
        input_folder_var.set(folder)
        expected_default_output = os.path.dirname(folder)
        
        if not output_folder_var.get() or output_folder_var.get() == expected_default_output:
            output_folder_var.set(expected_default_output)

def select_output_folder():
    """Manually select an output folder."""
    folder = filedialog.askdirectory()
    if folder:
        output_folder_var.set(folder)

def update_output_language_entry(*args):
    """Enable/Disable manual input for Output Language Folder."""
    if output_language_var.get() == "Manual":
        output_language_manual_entry.config(state="normal")
    else:
        output_language_manual_var.set("")  # Clear manual input
        output_language_manual_entry.config(state="disabled")

# Create GUI Window
root = tk.Tk()
root.title("CHS ↔ ZHTW Converter")
root.geometry("1000x700")
root.resizable(True, True)

# Apply Dark Theme
root.configure(bg="#2B2B2B")

style = ttk.Style()
style.theme_use("clam")
style.configure("TButton", font=("Arial", 14), padding=5)
style.configure("TLabel", font=("Arial", 16), background="#2B2B2B", foreground="white")
style.configure("TEntry", font=("Arial", 14), padding=5)
style.configure("TCombobox", font=("Arial", 14), padding=5)

# Grid Configuration for Responsiveness
root.columnconfigure(1, weight=1)
root.rowconfigure(5, weight=1)

# Input Folder
ttk.Label(root, text="📂 Input Folder:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
input_folder_var = tk.StringVar(value=default_steam_folder)
entry_input = ttk.Entry(root, textvariable=input_folder_var)
entry_input.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
btn_input = ttk.Button(root, text="Browse", command=select_input_folder)
btn_input.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
btn_input.bind("<Configure>", lambda e: btn_input.config(height=entry_input.winfo_height()))

# Output Folder
ttk.Label(root, text="📁 Output Folder Path:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
output_folder_var = tk.StringVar()
entry_output = ttk.Entry(root, textvariable=output_folder_var)
entry_output.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
btn_output = ttk.Button(root, text="Browse", command=select_output_folder)
btn_output.grid(row=1, column=2, padx=5, pady=5, sticky="ew")
btn_output.bind("<Configure>", lambda e: btn_output.config(height=entry_output.winfo_height()))

# Output Language Folder Selection
ttk.Label(root, text="🌐 Output Language Folder:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
output_language_var = tk.StringVar(value=output_language_options[1])
output_language_var.trace_add("write", update_output_language_entry)
output_language_dropdown = ttk.Combobox(root, textvariable=output_language_var, values=output_language_options, state="readonly")
output_language_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
output_language_manual_var = tk.StringVar()
output_language_manual_entry = ttk.Entry(root, textvariable=output_language_manual_var, state="disabled")
output_language_manual_entry.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

# File Type Selection
ttk.Label(root, text="📄 File Types (comma-separated):").grid(row=3, column=0, padx=10, pady=5, sticky="w")
file_types_var = tk.StringVar(value=".txt,.xml")
ttk.Entry(root, textvariable=file_types_var).grid(row=3, column=1, padx=5, pady=5, sticky="ew")

# Convert Button
ttk.Button(root, text="🚀 Start Conversion", command=log_message).grid(row=4, column=1, pady=20, sticky="ew")

# Log Output
log_text = scrolledtext.ScrolledText(root, height=20, font=("Arial", 14), bg="#1E1E1E", fg="white")
log_text.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

# Ensure log output expands correctly
root.rowconfigure(5, weight=1)

root.mainloop()

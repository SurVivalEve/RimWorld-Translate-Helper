import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import xml.etree.ElementTree as ET
import html # Import HTML parser for unescaping

# Constants
LABEL_WIDTH = 18  # Enough to align the "Output Language" label, etc.

# Default Paths
# CHANGED: now includes \294100 at the end by default
rimworld_mods_path = r"D:\SteamLibrary\steamapps\workshop\content\294100"

output_language_options = ["ChineseTraditional", "ChineseSimplified", "Manual"]
placeholder_options = ["TODO", "Original"]  # user can pick which placeholder approach to use

def log_message(message):
    """Logs messages in the UI."""
    log_text.insert(tk.END, message + "\n")
    log_text.see(tk.END)

def list_mods():
    """
    Finds all mod folders and extracts mod names from About.xml based on the selected mod path.
    Returns a list of strings "<folder> - <mod_name>".
    """
    global rimworld_mods_path
    mods = []
    if os.path.exists(rimworld_mods_path):
        for folder in os.listdir(rimworld_mods_path):
            mod_path = os.path.join(rimworld_mods_path, folder)
            about_path = os.path.join(mod_path, "About", "About.xml")
            mod_name = folder  # Default to folder name
            if os.path.exists(about_path):
                try:
                    tree = ET.parse(about_path)
                    root = tree.getroot()
                    name_element = root.find("name")
                    if name_element is not None:
                        mod_name = name_element.text.strip()
                except Exception as e:
                    log_message(f"⚠ Error reading {about_path}: {e}")
            mods.append(f"{folder} - {mod_name}")
    return mods

def refresh_mod_list():
    """Refreshes the mod dropdown list based on the current mod path."""
    mod_list = list_mods()
    mod_dropdown["values"] = mod_list
    search_var.set("")  # Clear search field
    log_message("Mod list refreshed.")

def filter_mod_list(*args):
    """Filters and auto-selects the first matching mod in the dropdown."""
    search_term = search_var.get().lower()
    full_list = list_mods()
    filtered_mods = [mod for mod in full_list if search_term in mod.lower()]
    mod_dropdown["values"] = filtered_mods
    if filtered_mods:
        mod_folder_var.set(filtered_mods[0])  # Auto-select first result

def open_workshop_page():
    """Opens the Steam Workshop page for the selected mod."""
    selected_mod = mod_folder_var.get().split(" - ")[0]  # Extract mod ID
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={selected_mod}"
    webbrowser.open(url)

def open_mod_folder():
    """Opens the selected mod folder in the file explorer."""
    selected_mod = mod_folder_var.get().split(" - ")[0]  # Extract mod ID
    mod_path = os.path.join(rimworld_mods_path, selected_mod)
    if os.path.exists(mod_path):
        os.startfile(mod_path)
    else:
        messagebox.showerror("Error", "Mod folder not found.")

def select_mod_folder():
    """Allows user to select the mod folder and updates the mod list accordingly."""
    global rimworld_mods_path
    new_path = filedialog.askdirectory(title="Select Mods Folder")
    if new_path:
        rimworld_mods_path = new_path
        log_message(f"Selected Mods Folder: {rimworld_mods_path}")
        refresh_mod_list()

def on_mod_selected(event=None):
    """Update the 'Output Folder' display when mod changes."""
    update_output_folder_display()

def on_language_selected(event=None):
    """Update the 'Output Folder' display when language changes or is typed manually."""
    if output_language_var.get() == "Manual":
        output_language_manual_entry.config(state="normal")
    else:
        output_language_manual_entry.config(state="disabled")
    update_output_folder_display()

def update_output_folder_display():
    """
    Show <SelectedMod>/Languages/<ChosenLanguage> in the "Output Folder" field,
    but do NOT actually create anything yet.
    """
    selected = mod_folder_var.get()
    if not selected:
        return

    mod_id = selected.split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, mod_id)

    chosen_lang = output_language_var.get()
    if chosen_lang == "Manual":
        manual_str = output_language_manual_var.get().strip()
        if not manual_str:
            manual_str = "English"
        chosen_lang = manual_str

    # Construct the would-be path:
    lang_path = os.path.join(mod_path, "Languages", chosen_lang)
    output_folder_var.set(lang_path)

def extract_translation():
    """
    Main "Extract" feature with these steps:
      1) Detect the mod's highest version folder or fallback 'Defs'.
      2) If the chosen language folder exists, ask user whether to delete or cancel.
      3) Rename 'DefLinked' -> 'DefInjected', 'CodeLinked' -> 'Keyed' if they exist.
         Remove old XML from them.
      4) Parse each .xml in the 'Defs' folder, gather sub-elements with 'label' or 'string' in their tag.
         Keep multi-level path. Write them to DefInjected/<DefType>/<filename>.

      5) Replicate 'Keyed' from English => chosen language
    """
    selected = mod_folder_var.get()
    if not selected:
        messagebox.showwarning("No Mod Selected", "Please select a mod from the dropdown first.")
        return

    mod_id = selected.split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, mod_id)
    if not os.path.exists(mod_path):
        messagebox.showerror("Error", f"Mod folder not found: {mod_path}")
        return

    chosen_lang = output_language_var.get()
    if chosen_lang == "Manual":
        manual_str = output_language_manual_var.get().strip()
        if not manual_str:
            manual_str = "English"
        chosen_lang = manual_str

    lang_folder_path = os.path.join(mod_path, "Languages", chosen_lang)

    # 1) Find the relevant Defs folder
    defs_source = find_defs_folder(mod_path)
    if not defs_source:
        log_message("No 'Defs' folder found in versioned or root folder. Extraction skipped.")
        return

    # 2) If the target language folder exists, ask user whether to delete or cancel
    if os.path.exists(lang_folder_path):
        answer = messagebox.askyesno(
            "Overwrite Language Folder?",
            f"The folder '{lang_folder_path}' already exists.\n\n"
            "Click YES to delete it and continue, NO to cancel."
        )
        if answer:
            try:
                shutil.rmtree(lang_folder_path)
                log_message(f"Deleted existing folder: {lang_folder_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete folder:\n{e}")
                return
        else:
            log_message("Extract canceled by user.")
            return

    # Now create it fresh
    os.makedirs(lang_folder_path, exist_ok=True)

    # 3) Rename 'DefLinked' => 'DefInjected', 'CodeLinked' => 'Keyed'
    def_injected_path = rename_if_exists(lang_folder_path, "DefLinked", "DefInjected")
    if not os.path.exists(def_injected_path):
        os.makedirs(def_injected_path, exist_ok=True)

    keyed_path = rename_if_exists(lang_folder_path, "CodeLinked", "Keyed")
    if not os.path.exists(keyed_path):
        os.makedirs(keyed_path, exist_ok=True)

    # Remove old XML in these two folders
    for folder_to_clear in [def_injected_path, keyed_path]:
        for root_dir, dirs, files in os.walk(folder_to_clear):
            for file in files:
                if file.lower().endswith(".xml"):
                    old_xml = os.path.join(root_dir, file)
                    try:
                        os.remove(old_xml)
                    except Exception as ex:
                        log_message(f"Error removing {old_xml}: {ex}")

    # 4) Parse each file in the 'Defs' folder
    for root_dir, dirs, files in os.walk(defs_source):
        for file in files:
            if file.lower().endswith(".xml"):
                src_path = os.path.join(root_dir, file)
                def_type, lines = parse_single_defs_file(src_path)
                if def_type and lines:
                    out_folder = os.path.join(def_injected_path, def_type)
                    os.makedirs(out_folder, exist_ok=True)
                    out_path = os.path.join(out_folder, file)  # preserve original name
                    write_translation_file(out_path, lines)

    # 5) Replicate Keyed from English => chosen language
    english_keyed_path = os.path.join(mod_path, "Languages", "English", "Keyed")
    replicate_keyed(english_keyed_path, keyed_path)

    messagebox.showinfo("Extraction Complete", f"Finished extracting translations to:\n{lang_folder_path}")
    log_message("Extraction finished.")

def find_defs_folder(mod_path):
    """Find the highest version folder with 'Defs', or fallback to mod root 'Defs'."""
    version_subfolders = []
    for entry in os.listdir(mod_path):
        full_path = os.path.join(mod_path, entry)
        if os.path.isdir(full_path):
            if re.match(r'^\d+(\.\d+)+$', entry.strip()):
                version_subfolders.append(entry.strip())

    def version_to_tuple(v):
        return tuple(int(x) for x in v.split("."))

    defs_folder = None
    if version_subfolders:
        version_subfolders.sort(key=lambda v: version_to_tuple(v))
        highest_version = version_subfolders[-1]
        possible = os.path.join(mod_path, highest_version, "Defs")
        if os.path.isdir(possible):
            defs_folder = possible

    if not defs_folder:
        root_defs = os.path.join(mod_path, "Defs")
        if os.path.isdir(root_defs):
            defs_folder = root_defs

    return defs_folder

def rename_if_exists(parent_folder, old_name, new_name):
    """If parent_folder/old_name exists, rename it to parent_folder/new_name."""
    old_path = os.path.join(parent_folder, old_name)
    new_path = os.path.join(parent_folder, new_name)
    if os.path.exists(old_path) and not os.path.exists(new_path):
        log_message(f"Renaming '{old_path}' -> '{new_path}'")
        shutil.move(old_path, new_path)
    return new_path

def should_extract_tag(tag_name):
    """Return True if tag_name == 'label' or 'string' in tag_name (case-insensitive)."""
    lower = tag_name.lower()
    if lower == "label":
        return True
    return ("string" in lower)

def parse_single_defs_file(xml_path):
    """
    BFS. If child is <label>, use child.text.
    If 'string' in tag => two cases:
       - no child tags => single-line => child.text
       - else => remove_outer_tag with ET.tostring(...) for sub-elements
    """
    try:
        with open(xml_path, "r", encoding="utf-8") as rf:
            file_data = rf.read()
        root = ET.fromstring(file_data)
        if root.tag != "Defs":
            return (None, None)

        def_type = None
        lines_collected = []

        for def_block in list(root):
            if def_type is None:
                def_type = def_block.tag

            def_name_elem = def_block.find("defName")
            if def_name_elem is None or not def_name_elem.text.strip():
                continue
            def_name = def_name_elem.text.strip()

            stack = [(def_block, [])]
            while stack:
                elem, path_so_far = stack.pop()
                for child in list(elem):
                    if child.tag != def_type:
                        next_path = path_so_far + [child.tag]
                    else:
                        next_path = path_so_far

                    stack.append((child, next_path))

                    if should_extract_tag(child.tag):
                        dotted_path = ".".join(next_path)
                        full_key = f"{def_name}.{dotted_path}"

                        if child.tag.lower() == "label":
                            extracted_text = (child.text or "").strip()
                        else:
                            # 'string' => check sub-elements
                            if not list(child) and child.text:
                                # no children => single-line
                                extracted_text = child.text.strip()
                            else:
                                # multi-line or has sub-tags => use remove_outer_tag
                                sub_raw = ET.tostring(child, encoding="unicode")
                                extracted_text = html.unescape(remove_outer_tag(sub_raw, child.tag))

                        comment_ = build_comment(extracted_text)
                        lines_ = extracted_text.splitlines()
                        lines_collected.append((comment_, full_key, lines_))

        if not lines_collected:
            return (None, None)
        return (def_type, lines_collected)
    except Exception as e:
        log_message(f"Error parsing {xml_path}: {e}")
        return (None, None)

def remove_outer_tag(raw_xml, tag):
    open_pat = re.compile(rf"<\s*{re.escape(tag)}(\s|>)")
    close_pat = re.compile(rf"</\s*{re.escape(tag)}\s*>")

    lines = raw_xml.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""

    if open_pat.search(lines[0]):
        lines.pop(0)
    if lines and close_pat.search(lines[-1]):
        lines.pop()

    return "\n".join(lines).strip("\r\n")

def build_comment(inside_text):
    inside_text = inside_text.strip("\r\n")
    if "\n" not in inside_text:
        return f"<!-- EN: {inside_text.strip()} -->" if inside_text else "<!-- EN: -->"

    # **New Fix**: Trim leading spaces only, not structure
    lines = [ln.lstrip() for ln in inside_text.split("\n")]
    joined = "\n".join(lines)
    return "<!-- EN:\n" + joined + "\n-->"


def write_translation_file(out_path, lines):
    mode = placeholder_var.get()
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<LanguageData>\n\n')

            for (comment, key, originalLines) in lines:
                f.write(f"  {comment}\n")

                if mode == "TODO":
                    f.write(f"  <{key}>TODO</{key}>\n\n")
                else:
                    if not originalLines:
                        f.write(f"  <{key}>TODO</{key}>\n\n")
                    else:
                        # **Fix: Trim spaces and apply CDATA for XML-like content**
                        cleaned_lines = [ln.lstrip() for ln in originalLines]
                        needs_cdata = any("<" in ln or ">" in ln for ln in cleaned_lines)

                        if len(cleaned_lines) == 1:
                            content = cleaned_lines[0]
                            if needs_cdata:
                                f.write(f"  <{key}><![CDATA[{content}]]></{key}>\n\n")
                            else:
                                f.write(f"  <{key}>{content}</{key}>\n\n")
                        else:
                            f.write(f"  <{key}>\n")
                            for ln in cleaned_lines:
                                if needs_cdata:
                                    f.write(f"    <![CDATA[{ln}]]>\n")
                                else:
                                    f.write(f"    {ln}\n")
                            f.write(f"  </{key}>\n\n")

            f.write("</LanguageData>\n")
        log_message(f"Created: {out_path}")
    except Exception as e:
        log_message(f"Error writing {out_path}: {e}")



# -------------------
# Keyed Replication
# -------------------

def parse_single_keyed_file(xml_path):
    results = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        if root.tag != "LanguageData":
            return results
        for child in root:
            tag_name = child.tag
            original_text = (child.text or "").strip()
            cmt = build_comment(original_text)
            results.append((cmt, tag_name, original_text))
    except Exception as e:
        log_message(f"Error parsing Keyed file {xml_path}: {e}")
    return results

def write_keyed_file(out_path, entries):
    mode = placeholder_var.get()
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<LanguageData>\n\n')

            for (comment, tag_name, original_text) in entries:
                f.write(f"  {comment}\n")
                if mode == "TODO":
                    f.write(f"  <{tag_name}>TODO</{tag_name}>\n\n")
                else:
                    if not original_text.strip():
                        f.write(f"  <{tag_name}>TODO</{tag_name}>\n\n")
                    else:
                        lines = original_text.splitlines()
                        if len(lines) == 1:
                            f.write(f"  <{tag_name}>{lines[0]}</{tag_name}>\n\n")
                        else:
                            f.write(f"  <{tag_name}>\n")
                            for ln in lines:
                                f.write(f"    {ln}\n")
                            f.write(f"  </{tag_name}>\n\n")

            f.write("</LanguageData>\n")
        log_message(f"Created Keyed file: {out_path}")
    except Exception as e:
        log_message(f"Error writing Keyed file {out_path}: {e}")

def replicate_keyed(english_keyed_path, chosen_keyed_path):
    if not os.path.isdir(english_keyed_path):
        log_message(f"No English Keyed folder found at: {english_keyed_path}, skipping Keyed replication.")
        return

    log_message(f"Replicating Keyed from {english_keyed_path} => {chosen_keyed_path}")
    for root_dir, dirs, files in os.walk(english_keyed_path):
        rel = os.path.relpath(root_dir, english_keyed_path)
        for file in files:
            if file.lower().endswith(".xml"):
                src_file = os.path.join(root_dir, file)
                entries = parse_single_keyed_file(src_file)
                if entries:
                    out_dir = os.path.join(chosen_keyed_path, rel)
                    os.makedirs(out_dir, exist_ok=True)
                    out_file = os.path.join(out_dir, file)
                    write_keyed_file(out_file, entries)

# ----------------------------------------------
# GUI Window
# ----------------------------------------------
root = tk.Tk()
root.title("RimWorld Translation Extractor")
root.geometry("1000x700")
root.resizable(True, True)
root.configure(bg="#2B2B2B")

style = ttk.Style()
style.theme_use("clam")

style.configure("TFrame", background="#2B2B2B")
style.configure("TLabel", font=("Arial", 16), background="#2B2B2B", foreground="white")
style.configure("TButton", 
                font=("Arial", 14), 
                padding=6, 
                background="#4A4A4A", 
                foreground="white", 
                borderwidth=0, 
                relief="flat")

style.configure("TEntry", 
                font=("Arial", 14), 
                padding=6, 
                foreground="white", 
                fieldbackground="#333333",
                insertcolor="white")

style.map("TEntry",
          foreground=[("readonly", "white"), ("disabled", "grey")],
          background=[("readonly", "#333333"), ("disabled", "#333333")])

style.configure("TCombobox", 
                font=("Arial", 14), 
                padding=6, 
                foreground="white", 
                fieldbackground="#333333", 
                selectbackground="#555555", 
                selectforeground="white", 
                arrowcolor="white")

style.map("TCombobox",
          background=[("readonly", "#333333"), ("disabled", "#333333")],
          fieldbackground=[("readonly", "#333333"), ("disabled", "#333333")],
          selectbackground=[("readonly", "#555555")],
          selectforeground=[("readonly", "white")])

# Top Frame: Mods Folder
mod_folder_frame = ttk.Frame(root, padding="10")
mod_folder_frame.pack(pady=10, fill="x")

ttk.Label(mod_folder_frame, text="📁 Mods Folder:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=0, sticky="w")
mod_folder_var_display = tk.StringVar(value=rimworld_mods_path)
mod_folder_entry = ttk.Entry(mod_folder_frame, textvariable=mod_folder_var_display, width=60, state="readonly")
mod_folder_entry.grid(column=1, row=0, padx=(10, 0), sticky="ew")
ttk.Button(mod_folder_frame, text="Browse", command=select_mod_folder).grid(column=2, row=0, padx=5)
mod_folder_frame.columnconfigure(1, weight=1)

# Search Frame: Search & Select
search_frame = ttk.Frame(root, padding="10")
search_frame.pack(pady=10, fill="x")

# Search
ttk.Label(search_frame, text="🔍 Search Mod:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=0, sticky="w")
search_var = tk.StringVar()
search_entry = ttk.Entry(search_frame, textvariable=search_var, width=70)
search_entry.grid(column=1, row=0, padx=(10, 0), sticky="ew")
search_var.trace("w", lambda *args: filter_mod_list())

# Mod Dropdown
ttk.Label(search_frame, text="📂 Select Mod:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=1, sticky="w")
mod_folder_var = tk.StringVar()
mod_dropdown = ttk.Combobox(search_frame, textvariable=mod_folder_var, values=[], state="readonly", width=70)
mod_dropdown.grid(column=1, row=1, padx=(10, 0), sticky="ew")
mod_dropdown['values'] = list_mods()
mod_dropdown.bind("<<ComboboxSelected>>", on_mod_selected)
search_frame.columnconfigure(1, weight=1)

# Language Frame
language_frame = ttk.Frame(root, padding="10")
language_frame.pack(pady=10, fill="x")

ttk.Label(language_frame, text="🌐 Output Language:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=0, sticky="w")
output_language_var = tk.StringVar(value=output_language_options[0])  # default = ChineseTraditional
language_combo = ttk.Combobox(language_frame, textvariable=output_language_var, 
                              values=output_language_options, state="readonly", width=60)
language_combo.grid(column=1, row=0, padx=(10, 0), sticky="ew")

# Custom entry for "Manual" language
output_language_manual_var = tk.StringVar()
output_language_manual_entry = ttk.Entry(language_frame, textvariable=output_language_manual_var, state="disabled", width=60)
output_language_manual_entry.grid(column=1, row=1, padx=(10, 0), sticky="ew")

language_combo.bind("<<ComboboxSelected>>", on_language_selected)
language_frame.columnconfigure(1, weight=1)

# Output Frame
output_frame = ttk.Frame(root, padding="10")
output_frame.pack(pady=10, fill="x")

ttk.Label(output_frame, text="📁 Output Folder:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=0, sticky="w")
output_folder_var = tk.StringVar()
output_folder_entry = ttk.Entry(output_frame, textvariable=output_folder_var, width=60)
output_folder_entry.grid(column=1, row=0, padx=(10, 0), sticky="ew")
ttk.Button(output_frame, text="Browse", 
           command=lambda: output_folder_var.set(filedialog.askdirectory())).grid(column=2, row=0, padx=5)
output_frame.columnconfigure(1, weight=1)

# Placeholder Frame
placeholder_frame = ttk.Frame(root, padding="10")
placeholder_frame.pack(pady=10, fill="x")

ttk.Label(placeholder_frame, text="Placeholder Mode:", width=LABEL_WIDTH, anchor="w").grid(column=0, row=0, sticky="w")
placeholder_var = tk.StringVar(value=placeholder_options[0])  # default "TODO"
placeholder_combo = ttk.Combobox(placeholder_frame, textvariable=placeholder_var, 
                                 values=placeholder_options, state="readonly", width=60)
placeholder_combo.grid(column=1, row=0, padx=(10, 0), sticky="ew")
placeholder_frame.columnconfigure(1, weight=1)

# Button Frame
button_frame = ttk.Frame(root, padding="10")
button_frame.pack(fill="x")

ttk.Button(button_frame, text="Refresh Mod List", command=refresh_mod_list, width=20).grid(column=0, row=0, padx=5)
ttk.Button(button_frame, text="Open Workshop Page", command=open_workshop_page, width=20).grid(column=1, row=0, padx=5)
ttk.Button(button_frame, text="Open Mod Folder", command=open_mod_folder, width=20).grid(column=2, row=0, padx=5)
ttk.Button(button_frame, text="Extract", command=extract_translation, width=20).grid(column=3, row=0, padx=5)

log_text = scrolledtext.ScrolledText(root, height=10, font=("Arial", 14), bg="#1E1E1E", fg="white", wrap=tk.WORD, insertbackground="white")
log_text.pack(expand=True, fill="both", padx=10, pady=10)

update_output_folder_display()
root.mainloop()

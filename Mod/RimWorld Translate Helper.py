#!/usr/bin/env python3
"""
RimWorld Translate Helper
-------------------------

Features:
  1. An OpenCC converter to convert text files between Simplified and Traditional Chinese.
  2. A translator/extractor for RimWorld mods that extracts, merges, and compares XML language files.

Sections:
  1. Global Constants & Default Paths
  2. Custom Exceptions
  3. Utility Functions (XML parsing and comment handling)
  4. File Writing & Merging Functions
  5. Translation Extraction Functions
  6. Logging Functions (color‐coded output)
  7. GUI Setup & Main Application Window
"""

import os
import re
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import webbrowser
import opencc
import xml.etree.ElementTree as ET
import html
import tempfile

# ------------------------------
# 1. GLOBAL CONSTANTS & DEFAULT PATHS
# ------------------------------
LABEL_WIDTH = 28

default_steam_folder = r"D:\SteamLibrary\steamapps\workshop\content"
rimworld_mods_path = r"D:\SteamLibrary\steamapps\workshop\content\294100"

output_language_options_converter = ["ChineseTraditional", "ChineseSimplified", "Manual"]
output_language_options_translator = ["ChineseTraditional", "ChineseSimplified", "Manual"]
placeholder_options = ["TODO", "Original"]
submod_naming_options = ["None", "Prefix", "Suffix"]
update_mode_options = ["Merge", "Replace"]

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

# Global variables for conflict resolution and extraction cancellation
conflict_resolution_global = None
extraction_cancelled = False

# Toggle for detailed logging
ENABLE_DETAILED_FILE_LOGS = True  # Default: True

# ------------------------------
# 2. CUSTOM EXCEPTIONS
# ------------------------------
class ExtractionCancelledException(Exception):
    """Raised when the user cancels the extraction process."""
    pass

# ------------------------------
# 3. UTILITY FUNCTIONS (XML Parsing & Comment Handling)
# ------------------------------
def build_comment(inside_text):
    inside_text = inside_text.strip("\r\n")
    if "\n" not in inside_text:
        return f"<!-- EN: {inside_text.strip()} -->" if inside_text else "<!-- EN: -->"
    lines = [ln.lstrip() for ln in inside_text.split("\n")]
    return "<!-- EN:\n" + "\n".join(lines) + "\n-->"

def fix_comment(cmt):
    if isinstance(cmt, str):
        s = cmt.strip()
        if s.startswith("<!--") and s.endswith("-->"):
            return s
        return build_comment(s)
    else:
        try:
            s = ET.tostring(cmt, encoding="unicode").strip()
            if s.startswith("<!--") and s.endswith("-->"):
                return s
            return build_comment(s)
        except Exception:
            return str(cmt).strip()

def parse_single_keyed_file(xml_path):
    results = []
    current_comment = None
    try:
        context = ET.iterparse(xml_path, events=("start", "comment"))
        for event, elem in context:
            if event == "comment":
                current_comment = fix_comment(elem)
            elif event == "start":
                if elem.tag == "LanguageData":
                    continue
                text = (elem.text or "").strip()
                comment = current_comment if current_comment else build_comment(text)
                results.append((comment, elem.tag, text))
                current_comment = None
        return results
    except Exception as e:
        log_message(translator_log_text, f"Error parsing keyed file {xml_path}: {e}", "error")
        return results

def should_extract_tag(tag_name):
    lower = tag_name.lower()
    return (lower in ("label", "description")) or ("string" in lower)

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

def parse_single_defs_file(xml_path):
    """
    Extract translation entries from a RimWorld Defs XML file using iterative parsing.
    Returns (def_type, list_of_entries) or (None, None).
    """
    try:
        context = ET.iterparse(xml_path, events=("start", "end"))
        root = None
        current_def = None
        def_type = None
        lines_collected = []
        def_name = None

        for event, elem in context:
            if root is None:
                root = elem
                if root.tag != "Defs":
                    return (None, None)
                continue

            if event == "start" and def_type is None:
                if elem is not None and elem is not root:
                    def_type = elem.tag

            if event == "start" and elem.tag == "defName":
                current_def = elem
            elif event == "end":
                if elem.tag == "defName" and current_def is elem:
                    def_name = (elem.text or "").strip()
                elif def_name and should_extract_tag(elem.tag):
                    path_list = []
                    parent = elem
                    while parent is not None and parent is not root:
                        path_list.append(parent.tag)
                        parent = parent.getparent() if hasattr(parent, "getparent") else None
                    path_list.reverse()
                    if len(path_list) > 1 and path_list[0] == "Defs":
                        path_list = path_list[1:]
                    if path_list and path_list[0] == def_type:
                        path_list = path_list[1:]
                    if len(path_list) > 1:
                        dotted_path = ".".join(path_list[1:])
                    else:
                        dotted_path = path_list[-1] if path_list else elem.tag

                    if not list(elem) and elem.text:
                        extracted_text = elem.text.strip()
                    else:
                        sub_raw = ET.tostring(elem, encoding="unicode")
                        extracted_text = html.unescape(remove_outer_tag(sub_raw, elem.tag))
                    comment_ = build_comment(extracted_text)
                    lines_ = extracted_text.splitlines()
                    full_key = f"{def_name}.{dotted_path}"
                    lines_collected.append((comment_, full_key, lines_))

                if elem.tag == def_type:
                    def_name = None

        if not lines_collected:
            return (None, None)
        return (def_type, lines_collected)
    except Exception as e:
        log_message(translator_log_text, f"Error parsing {xml_path}: {e}", "error")
        return (None, None)

# ------------------------------
# 4. FILE WRITING & MERGING FUNCTIONS
# ------------------------------
def write_translation_file(out_path, lines):
    mode = translator_placeholder_var.get()  # "TODO" or "Original"
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        sorted_entries = sorted(lines, key=lambda x: x[1])
        with open(out_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<LanguageData>\n')
            for (comment, key, originalLines) in sorted_entries:
                f.write(f"  {comment}\n")
                if mode == "TODO":
                    f.write(f"  <{key}>TODO</{key}>\n")
                else:
                    if not originalLines:
                        f.write(f"  <{key}>TODO</{key}>\n")
                    else:
                        cleaned_lines = [ln.strip() for ln in originalLines if ln.strip()]
                        needs_cdata = any("<" in ln or ">" in ln for ln in cleaned_lines)
                        if len(cleaned_lines) == 1:
                            content = cleaned_lines[0]
                            if needs_cdata:
                                f.write(f"  <{key}><![CDATA[{content}]]></{key}>\n")
                            else:
                                f.write(f"  <{key}>{content}</{key}>\n")
                        else:
                            f.write(f"  <{key}>\n")
                            for ln in cleaned_lines:
                                ln = ln.strip()
                                if needs_cdata:
                                    f.write(f"    <![CDATA[{ln}]]>\n")
                                else:
                                    f.write(f"    {ln}\n")
                            f.write(f"  </{key}>\n")
            f.write('</LanguageData>\n')
        if ENABLE_DETAILED_FILE_LOGS:
            log_message(translator_log_text, f"Created translation file: {out_path}", "success")
    except Exception as e:
        log_message(translator_log_text, f"Error writing {out_path}: {e}", "error")

def merge_translation_file(existing_file, new_entries):
    parsed_existing = parse_single_keyed_file(existing_file)
    existing = {}
    if parsed_existing:
        for (cmt, key, text) in parsed_existing:
            fixed_cmt = fix_comment(cmt)
            text_str = text.strip() if isinstance(text, str) else "\n".join(text).strip()
            existing[key] = (fixed_cmt, text_str.splitlines(), text_str)

    mode = translator_placeholder_var.get()
    merged = {}

    for (new_cmt, key, lines) in new_entries:
        new_cmt_str = fix_comment(new_cmt)
        new_val = "\n".join(lines).strip()
        if key in existing:
            existing_val = existing[key][2]
            if mode == "TODO":
                if existing_val != "TODO":
                    merged[key] = existing[key]
                else:
                    if new_val != "TODO":
                        merged[key] = (new_cmt_str, new_val.splitlines(), new_val)
                    else:
                        merged[key] = existing[key]
            else:
                if existing_val == new_val:
                    merged[key] = existing[key]
                else:
                    merged[key] = (new_cmt_str, new_val.splitlines(), new_val)
        else:
            if new_val != "TODO":
                merged[key] = (new_cmt_str, new_val.splitlines(), new_val)

    for k, v in existing.items():
        if k not in merged:
            merged[k] = v

    combined = []
    for k in sorted(merged.keys()):
        cmt, txt, _ = merged[k]
        combined.append((cmt, k, txt if isinstance(txt, list) else txt.splitlines()))
    write_translation_file(existing_file, combined)

def write_keyed_file(out_path, entries):
    mode = translator_placeholder_var.get()
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<LanguageData>\n')
            for (comment, tag_name, original_text) in entries:
                f.write(f"  {comment}\n")
                if mode == "TODO":
                    f.write(f"  <{tag_name}>TODO</{tag_name}>\n")
                else:
                    if not original_text.strip():
                        f.write(f"  <{tag_name}>TODO</{tag_name}>\n")
                    else:
                        lines = original_text.splitlines()
                        if len(lines) == 1:
                            f.write(f"  <{tag_name}>{lines[0]}</{tag_name}>\n")
                        else:
                            f.write(f"  <{tag_name}>\n")
                            for ln in lines:
                                ln = ln.strip()
                                f.write(f"    {ln}\n")
                            f.write(f"  </{tag_name}>\n")
            f.write('</LanguageData>\n')
        if ENABLE_DETAILED_FILE_LOGS:
            log_message(translator_log_text, f"Created keyed file: {out_path}", "success")
    except Exception as e:
        log_message(translator_log_text, f"Error writing keyed file {out_path}: {e}", "error")

def replicate_keyed(english_keyed_path, chosen_keyed_path):
    if not os.path.isdir(english_keyed_path):
        log_message(translator_log_text, f"No English Keyed folder at: {english_keyed_path}. Skipping.", "warning")
        return
    update_mode = translator_update_mode_var.get()
    log_message(translator_log_text, f"Replicating keyed from {english_keyed_path} to {chosen_keyed_path}", "info")

    for root_dir, _, files in os.walk(english_keyed_path):
        rel = os.path.relpath(root_dir, english_keyed_path)
        out_dir = os.path.join(chosen_keyed_path, rel)
        os.makedirs(out_dir, exist_ok=True)
        for file in files:
            if file.lower().endswith(".xml"):
                src_file = os.path.join(root_dir, file)
                entries = parse_single_keyed_file(src_file)
                if entries:
                    out_file = os.path.join(out_dir, file)
                    if update_mode == "Merge" and os.path.exists(out_file):
                        merge_translation_file(out_file, entries)
                    else:
                        write_keyed_file(out_file, entries)

def find_defs_folder(mod_path):
    root_defs = os.path.join(mod_path, "Defs")
    if os.path.isdir(root_defs):
        return root_defs

    version_subfolders = []
    for entry in os.listdir(mod_path):
        full_path = os.path.join(mod_path, entry)
        if os.path.isdir(full_path) and re.match(r'^\d+(\.\d+)+$', entry.strip()):
            version_subfolders.append(entry.strip())

    if version_subfolders:
        def version_to_tuple(v):
            return tuple(int(x) for x in v.split("."))
        version_subfolders.sort(key=version_to_tuple)
        highest_version = version_subfolders[-1]
        possible = os.path.join(mod_path, highest_version, "Defs")
        if os.path.isdir(possible):
            return possible
    return None

# ------------------------------
# 5. TRANSLATION EXTRACTION FUNCTIONS
# ------------------------------
def translator_list_mods():
    mods = []
    if os.path.exists(rimworld_mods_path):
        for folder in os.listdir(rimworld_mods_path):
            mod_path = os.path.join(rimworld_mods_path, folder)
            about_path = os.path.join(mod_path, "About", "About.xml")
            mod_name = folder
            if os.path.exists(about_path):
                try:
                    tree = ET.parse(about_path)
                    root_xml = tree.getroot()
                    name_element = root_xml.find("name")
                    if name_element is not None and name_element.text:
                        mod_name = name_element.text.strip()
                except Exception as e:
                    log_message(translator_log_text, f"Error reading {about_path}: {e}", "error")
            mods.append(f"{folder} - {mod_name}")
    return mods

def filter_mod_list(*_):
    search_term = translator_search_var.get().lower()
    full_list = translator_list_mods()
    filtered_mods = [m for m in full_list if search_term in m.lower()]
    translator_mod_dropdown["values"] = filtered_mods
    translator_mod_folder_var.set(filtered_mods[0] if filtered_mods else "")

def rename_if_exists(parent_folder, old_name, new_name):
    old_path = os.path.join(parent_folder, old_name)
    new_path = os.path.join(parent_folder, new_name)
    if os.path.exists(old_path) and not os.path.exists(new_path):
        log_message(translator_log_text, f"Renaming '{old_path}' to '{new_path}'", "info")
        shutil.move(old_path, new_path)
    return new_path

def ask_conflict_resolution(prompt):
    global conflict_resolution_global
    if conflict_resolution_global is not None:
        return conflict_resolution_global

    dialog = tk.Toplevel(root)
    dialog.title("File Conflict")
    lbl = tk.Label(dialog, text=prompt, wraplength=400)
    lbl.pack(padx=10, pady=10)
    var_apply = tk.IntVar()
    cb = tk.Checkbutton(dialog, text="Apply to all", variable=var_apply)
    cb.pack(pady=5)
    result = {"option": None}

    def choose(opt):
        global conflict_resolution_global
        result["option"] = opt
        if var_apply.get():
            conflict_resolution_global = opt
        dialog.destroy()

    btn_frame = tk.Frame(dialog)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Merge", command=lambda: choose("merge")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Prefix", command=lambda: choose("prefix")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Suffix", command=lambda: choose("suffix")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Skip", command=lambda: choose("skip")).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel Extraction", command=lambda: choose("cancel")).pack(side="left", padx=5)

    dialog.update_idletasks()
    dw = dialog.winfo_reqwidth()
    dh = dialog.winfo_reqheight()
    sw = dialog.winfo_screenwidth()
    sh = dialog.winfo_screenheight()
    x = (sw // 2) - (dw // 2)
    y = (sh // 2) - (dh // 2)
    dialog.geometry(f"{dw}x{dh}+{x}+{y}")
    dialog.grab_set()
    dialog.wait_window()
    return result["option"]

def _handle_file_conflict(candidate_path, submod_name, lines):
    global conflict_resolution_global
    while os.path.exists(candidate_path):
        choice = conflict_resolution_global or ask_conflict_resolution(
            f"File '{os.path.basename(candidate_path)}' already exists for sub-mod '{submod_name}'.\nChoose an option:"
        )
        if choice == "cancel":
            raise ExtractionCancelledException
        elif choice == "skip":
            log_message(translator_log_text, f"Skipping '{os.path.basename(candidate_path)}' due to conflict.", "info")
            return None
        elif choice == "merge":
            log_message(translator_log_text, "Merging file (conflict resolution).", "info")
            merge_translation_file(candidate_path, lines)
            return candidate_path
        elif choice == "prefix":
            folder = os.path.dirname(candidate_path)
            base = os.path.basename(candidate_path)
            name, ext = os.path.splitext(base)
            prefix_str = f"{submod_name}_"
            if not name.startswith(prefix_str):
                name = prefix_str + name
                candidate_path = os.path.join(folder, name + ext)
            else:
                i = 2
                new_candidate = os.path.join(folder, f"{name}_{i}{ext}")
                while os.path.exists(new_candidate):
                    i += 1
                    new_candidate = os.path.join(folder, f"{name}_{i}{ext}")
                candidate_path = new_candidate
        elif choice == "suffix":
            folder = os.path.dirname(candidate_path)
            base = os.path.basename(candidate_path)
            name, ext = os.path.splitext(base)
            suffix_str = f"_{submod_name}"
            if not name.endswith(suffix_str):
                name += suffix_str
                candidate_path = os.path.join(folder, name + ext)
            else:
                i = 2
                new_candidate = os.path.join(folder, f"{name}_{i}{ext}")
                while os.path.exists(new_candidate):
                    i += 1
                    new_candidate = os.path.join(folder, f"{name}_{i}{ext}")
                candidate_path = new_candidate
        else:
            return None
    return candidate_path

def translator_extract_translation(dest_folder=None, simulate=False):
    global extraction_cancelled
    extraction_cancelled = False

    selected = translator_mod_folder_var.get()
    if not selected:
        messagebox.showwarning("No Mod Selected", "Please select a mod.")
        return

    mod_id = selected.split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, mod_id)
    if not os.path.exists(mod_path):
        messagebox.showerror("Error", f"Mod folder not found: {mod_path}")
        return

    chosen_lang = translator_output_language_var.get()
    if chosen_lang == "Manual":
        manual_str = translator_output_language_manual_var.get().strip() or "English"
        chosen_lang = manual_str

    lang_folder_path = os.path.join(mod_path, "Languages", chosen_lang) if dest_folder is None else dest_folder
    update_mode = translator_update_mode_var.get()

    if update_mode == "Replace":
        if os.path.exists(lang_folder_path) and not simulate:
            answer = messagebox.askyesno(
                "Overwrite Language Folder?",
                f"The folder '{lang_folder_path}' already exists.\nClick YES to delete it and continue, NO to cancel."
            )
            if answer:
                try:
                    shutil.rmtree(lang_folder_path)
                    log_message(translator_log_text, f"Deleted folder: {lang_folder_path}", "info")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to delete:\n{e}")
                    return
            else:
                log_message(translator_log_text, "Extraction cancelled by user.", "warning")
                return
        elif os.path.exists(lang_folder_path) and simulate:
            try:
                shutil.rmtree(lang_folder_path)
                log_message(translator_log_text, f"(Simulate) Deleted folder: {lang_folder_path}", "info")
            except Exception as e:
                log_message(translator_log_text, f"(Simulate) Error deleting folder: {e}", "error")
                return
    else:
        log_message(translator_log_text, "Update Mode: Merge. Existing translations will be merged.", "info")

    os.makedirs(lang_folder_path, exist_ok=True)
    def_injected_path = rename_if_exists(lang_folder_path, "DefLinked", "DefInjected")
    os.makedirs(def_injected_path, exist_ok=True)
    keyed_path = rename_if_exists(lang_folder_path, "CodeLinked", "Keyed")
    os.makedirs(keyed_path, exist_ok=True)

    if update_mode == "Replace":
        for folder_to_clear in [def_injected_path, keyed_path]:
            for root_dir, _, files in os.walk(folder_to_clear):
                for file in files:
                    if file.lower().endswith(".xml"):
                        old_xml = os.path.join(root_dir, file)
                        try:
                            os.remove(old_xml)
                        except Exception as ex:
                            log_message(translator_log_text, f"Error removing {old_xml}: {ex}", "error")

    defs_source = find_defs_folder(mod_path)
    if not defs_source:
        log_message(translator_log_text, "No 'Defs' folder found. Skipping extraction.", "warning")
        return

    try:
        for root_dir, _, files in os.walk(defs_source):
            if extraction_cancelled:
                raise ExtractionCancelledException
            for file in files:
                if file.lower().endswith(".xml"):
                    src_path = os.path.join(root_dir, file)
                    def_type, lines = parse_single_defs_file(src_path)
                    if def_type and lines:
                        out_folder = os.path.join(def_injected_path, def_type)
                        os.makedirs(out_folder, exist_ok=True)
                        out_path = os.path.join(out_folder, file)
                        if update_mode == "Merge" and os.path.exists(out_path):
                            merge_translation_file(out_path, lines)
                        else:
                            write_translation_file(out_path, lines)

        replicate_keyed(os.path.join(mod_path, "Languages", "English", "Keyed"), keyed_path)
        log_message(translator_log_text, "Main mod extraction finished.", "success")

        submods_root = None
        potential_mods_folder = os.path.join(mod_path, "Mods")
        if os.path.isdir(potential_mods_folder):
            submods_root = potential_mods_folder
        else:
            version_subfolders = [
                entry.strip()
                for entry in os.listdir(mod_path)
                if os.path.isdir(os.path.join(mod_path, entry)) and re.match(r'^\d+(\.\d+)+$', entry.strip())
            ]
            if version_subfolders:
                def version_to_tuple(v):
                    return tuple(int(x) for x in v.split("."))
                version_subfolders.sort(key=version_to_tuple)
                highest_version = version_subfolders[-1]
                maybe = os.path.join(mod_path, highest_version, "Mods")
                if os.path.isdir(maybe):
                    submods_root = maybe

        if submods_root:
            log_message(translator_log_text, f"Processing submods in: {submods_root}", "info")
            for submod in os.listdir(submods_root):
                if extraction_cancelled:
                    raise ExtractionCancelledException
                submod_path = os.path.join(submods_root, submod)
                if os.path.isdir(submod_path):
                    log_message(translator_log_text, f"Processing sub-mod: {submod}", "info")
                    submod_defs = find_defs_folder(submod_path)
                    if not submod_defs:
                        log_message(translator_log_text, f"No 'Defs' folder for sub-mod '{submod}'. Skipping.", "warning")
                        continue

                    for root_d, _, f_list in os.walk(submod_defs):
                        if extraction_cancelled:
                            raise ExtractionCancelledException
                        for xml_file in f_list:
                            if xml_file.lower().endswith(".xml"):
                                src_path = os.path.join(root_d, xml_file)
                                def_type, lines = parse_single_defs_file(src_path)
                                if def_type and lines:
                                    out_folder = os.path.join(def_injected_path, def_type)
                                    os.makedirs(out_folder, exist_ok=True)
                                    naming_opt = translator_submod_naming_var.get()
                                    if naming_opt == "Prefix":
                                        candidate = f"{submod}_{xml_file}"
                                    elif naming_opt == "Suffix":
                                        base, ext = os.path.splitext(xml_file)
                                        candidate = f"{base}_{submod}{ext}"
                                    else:
                                        candidate = xml_file

                                    candidate_path = os.path.join(out_folder, candidate)
                                    final_path = _handle_file_conflict(candidate_path, submod, lines)
                                    if final_path is None:
                                        continue
                                    if update_mode == "Merge" and os.path.exists(final_path):
                                        merge_translation_file(final_path, lines)
                                    else:
                                        write_translation_file(final_path, lines)

                    submod_english_keyed = os.path.join(submod_path, "Languages", "English", "Keyed")
                    replicate_keyed(submod_english_keyed, keyed_path)
                    log_message(translator_log_text, f"Finished processing sub-mod: {submod}", "success")

        if not simulate:
            messagebox.showinfo("Extraction Complete", f"Finished extracting translations to:\n{lang_folder_path}")
        else:
            log_message(translator_log_text, "Simulation: Extraction complete.", "info")

    except ExtractionCancelledException:
        log_message(translator_log_text, "Extraction cancelled by user.", "warning")
        raise

def semantic_diff_file(existing_file, new_file):
    existing_entries = parse_single_keyed_file(existing_file)
    new_entries = parse_single_keyed_file(new_file)
    dict_existing = {key: text.strip() for (_, key, text) in existing_entries} if existing_entries else {}
    dict_new = {key: text.strip() for (_, key, text) in new_entries} if new_entries else {}

    lines = []
    for key in sorted(dict_new.keys()):
        if key not in dict_existing:
            lines.append(f"New key added: {key} => {dict_new[key]}")
    for key in sorted(dict_existing.keys()):
        if key not in dict_new:
            lines.append(f"Key removed: {key} (was: {dict_existing[key]})")
    for key in sorted(dict_existing.keys()):
        if key in dict_new and dict_existing[key] != dict_new[key]:
            lines.append(f"Key modified: {key}")
            lines.append(f"    Existing: {dict_existing[key]}")
            lines.append(f"    New: {dict_new[key]}")
    return "\n".join(lines)

def translator_deep_compare_extraction():
    selected = translator_mod_folder_var.get()
    if not selected:
        messagebox.showwarning("No Mod Selected", "Please select a mod first.")
        return

    mod_id = selected.split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, mod_id)
    chosen_lang = translator_output_language_var.get()
    if chosen_lang == "Manual":
        chosen_lang = translator_output_language_manual_var.get().strip() or "English"

    dest_folder = os.path.join(mod_path, "Languages", chosen_lang)
    with tempfile.TemporaryDirectory() as temp_dir:
        log_message(translator_log_text, f"Extracting to temporary folder: {temp_dir}", "info")
        translator_extract_translation(dest_folder=temp_dir, simulate=True)

        diff_report = ""
        for root_dir, _, files in os.walk(temp_dir):
            rel_path = os.path.relpath(root_dir, temp_dir)
            corr_dir = os.path.join(dest_folder, rel_path)
            for file in files:
                if file.lower().endswith(".xml"):
                    temp_file = os.path.join(root_dir, file)
                    dest_file = os.path.join(corr_dir, file)
                    if os.path.exists(dest_file):
                        report = semantic_diff_file(dest_file, temp_file)
                        if report:
                            diff_report += f"Diff: {os.path.join(rel_path, file)}\n{report}\n\n"
                    else:
                        diff_report += f"New file: {os.path.join(rel_path, file)}\n\n"

        for root_dir, _, files in os.walk(dest_folder):
            rel_path = os.path.relpath(root_dir, dest_folder)
            temp_dir2 = os.path.join(temp_dir, rel_path)
            for file in files:
                if file.lower().endswith(".xml") and not os.path.exists(os.path.join(temp_dir2, file)):
                    diff_report += f"File removed: {os.path.join(rel_path, file)}\n\n"

        if not diff_report:
            diff_report = "No differences found."

        diff_win = tk.Toplevel(root)
        diff_win.title("Deep Comparison Report")
        st = scrolledtext.ScrolledText(diff_win, font=("Arial", 12))
        st.pack(expand=True, fill="both")
        st.tag_config("new", foreground="green")
        st.tag_config("removed", foreground="red")
        st.tag_config("modified", foreground="purple")
        for line in diff_report.splitlines():
            start_idx = st.index("end-1c")
            st.insert(tk.END, line + "\n")
            if "New key added:" in line:
                st.tag_add("new", start_idx, st.index("end-1c"))
            elif "Key removed:" in line:
                st.tag_add("removed", start_idx, st.index("end-1c"))
            elif "Key modified:" in line:
                st.tag_add("modified", start_idx, st.index("end-1c"))
        st.config(state="disabled")
        diff_win.geometry("800x600")

# ------------------------------
# 6. LOGGING FUNCTIONS
# ------------------------------
def log_message(widget, message, level="info"):
    widget.insert(tk.END, message + "\n", level)
    widget.see(tk.END)

# ------------------------------
# 7. GUI SETUP & MAIN APPLICATION WINDOW
# ------------------------------
root = tk.Tk()
root.title("RimWorld Translate Helper")
# Set default window size to 1920x1080
root.geometry("1920x1080")
root.configure(bg="#2B2B2B")

style = ttk.Style()
style.theme_use("clam")
style.configure("TFrame", background="#2B2B2B")
style.configure("TLabel", font=("Arial", 16), background="#2B2B2B", foreground="white")
style.configure(
    "TButton",
    font=("Arial", 14),
    padding=6,
    background="#4A4A4A",
    foreground="white",
    borderwidth=0,
    relief="flat"
)
style.configure(
    "TEntry",
    font=("Arial", 14),
    padding=6,
    foreground="white",
    fieldbackground="#333333",
    insertcolor="white"
)
style.map("TEntry",
          foreground=[("readonly", "white"), ("disabled", "grey")],
          background=[("readonly", "#333333"), ("disabled", "#333333")])
style.configure(
    "TCombobox",
    font=("Arial", 14),
    padding=6,
    foreground="white",
    fieldbackground="#333333",
    selectbackground="#555555",
    selectforeground="white",
    arrowcolor="white"
)
style.map("TCombobox",
          background=[("readonly", "#333333"), ("disabled", "#333333")],
          fieldbackground=[("readonly", "#333333"), ("disabled", "#333333")],
          selectbackground=[("readonly", "#555555")],
          selectforeground=[("readonly", "white")])

notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both")

# 7.1 OpenCC Converter Tab
tab_converter = ttk.Frame(notebook)
notebook.add(tab_converter, text="📜 OpenCC Converter")

converter_input_folder_var = tk.StringVar(value=default_steam_folder)
converter_output_folder_var = tk.StringVar()
converter_output_language_var = tk.StringVar(value=output_language_options_converter[0])
converter_output_language_manual_var = tk.StringVar()
converter_file_types_var = tk.StringVar(value=".txt,.xml")
opencc_mode_var = tk.StringVar(value=list(opencc_modes.keys())[0])

converter_log_text = scrolledtext.ScrolledText(
    tab_converter,
    height=10,
    font=("Arial", 14),
    bg="#1E1E1E",
    fg="white",
    wrap=tk.WORD
)
converter_log_text.grid(row=7, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

converter_log_text.tag_config("info", foreground="white")
converter_log_text.tag_config("warning", foreground="yellow")
converter_log_text.tag_config("error", foreground="red")
converter_log_text.tag_config("success", foreground="lightgreen")

def converter_select_input_folder():
    folder = filedialog.askdirectory(initialdir=default_steam_folder)
    if folder:
        converter_input_folder_var.set(folder)
        converter_update_output_folder()

def converter_select_output_folder():
    folder = filedialog.askdirectory()
    if folder:
        converter_output_folder_var.set(folder)

def converter_update_output_language_entry(*_):
    if converter_output_language_var.get() == "Manual":
        converter_output_language_manual_entry.config(state="normal")
    else:
        converter_output_language_manual_entry.set("")
        converter_output_language_manual_entry.config(state="disabled")
    converter_update_output_folder()

def converter_update_output_folder():
    input_folder = converter_input_folder_var.get()
    m = re.search(r"(.*[\\/](?:Languages)[\\/])([^\\/]+)$", input_folder)
    if m:
        base_path = m.group(1)
        out_lang = converter_output_language_var.get()
        if out_lang == "Manual":
            manual_str = converter_output_language_manual_var.get().strip() or "English"
            out_lang = manual_str
        new_out = os.path.join(base_path, out_lang)
        converter_output_folder_var.set(new_out)

def converter_start_conversion():
    input_folder = converter_input_folder_var.get()
    output_folder = converter_output_folder_var.get()
    if not input_folder or not output_folder:
        messagebox.showwarning("Missing Folders", "Please select both input and output folders.")
        return

    file_types = [ft.strip().lower() for ft in converter_file_types_var.get().split(",") if ft.strip()]
    mode = opencc_mode_var.get()
    config = opencc_modes.get(mode)
    if not config:
        messagebox.showerror("OpenCC Mode Error", f"Selected OpenCC mode is not available: {mode}")
        return

    try:
        cc_converter = opencc.OpenCC(config)
    except Exception as e:
        messagebox.showerror("OpenCC Error", f"Error initializing OpenCC with config {config}: {e}")
        return

    log_message(converter_log_text, f"Starting conversion: {mode} ({config})", "info")
    for root_dir, _, files in os.walk(input_folder):
        for file in files:
            if any(file.lower().endswith(ext) for ext in file_types):
                in_path = os.path.join(root_dir, file)
                try:
                    with open(in_path, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception as e:
                    log_message(converter_log_text, f"Error reading {in_path}: {e}", "error")
                    continue

                try:
                    converted_text = cc_converter.convert(text)
                except Exception as e:
                    log_message(converter_log_text, f"Error converting {in_path}: {e}", "error")
                    continue

                rel_path = os.path.relpath(root_dir, input_folder)
                out_dir = os.path.join(output_folder, rel_path)
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, file)
                try:
                    with open(out_path, "w", encoding="utf-8") as wf:
                        wf.write(converted_text)
                    if ENABLE_DETAILED_FILE_LOGS:
                        log_message(converter_log_text, f"Converted: {in_path} -> {out_path}", "success")
                except Exception as e:
                    log_message(converter_log_text, f"Error writing {out_path}: {e}", "error")

    if not os.path.exists(output_folder):
        try:
            os.makedirs(output_folder)
            log_message(converter_log_text, f"Created output folder: {output_folder}", "info")
        except Exception as e:
            messagebox.showerror("Folder Creation Error", f"Could not create output folder: {e}")
            return

    messagebox.showinfo("Conversion Complete", "OpenCC conversion is complete.")

ttk.Label(
    tab_converter, text="📂 Input Folder:", width=LABEL_WIDTH, anchor="w"
).grid(row=0, column=0, padx=10, pady=5, sticky="w")
input_entry = ttk.Entry(tab_converter, textvariable=converter_input_folder_var, width=60)
input_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
ttk.Button(tab_converter, text="Browse", command=converter_select_input_folder).grid(row=0, column=2, padx=5, pady=5, sticky="ew")

ttk.Label(
    tab_converter, text="📁 Output Folder:", width=LABEL_WIDTH, anchor="w"
).grid(row=1, column=0, padx=10, pady=5, sticky="w")
output_entry = ttk.Entry(tab_converter, textvariable=converter_output_folder_var, width=60)
output_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
ttk.Button(tab_converter, text="Browse", command=converter_select_output_folder).grid(row=1, column=2, padx=5, pady=5, sticky="ew")

ttk.Label(
    tab_converter, text="🌐 Output Language Folder:", width=LABEL_WIDTH, anchor="w"
).grid(row=2, column=0, padx=10, pady=5, sticky="w")
converter_output_language_var.trace_add("write", converter_update_output_language_entry)
output_lang_combo = ttk.Combobox(
    tab_converter,
    textvariable=converter_output_language_var,
    values=output_language_options_converter,
    state="readonly",
    width=40
)
output_lang_combo.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

converter_output_language_manual_entry = ttk.Entry(
    tab_converter, textvariable=converter_output_language_manual_var, state="disabled", width=20
)
converter_output_language_manual_entry.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

ttk.Label(
    tab_converter, text="📄 File Types:", width=LABEL_WIDTH, anchor="w"
).grid(row=3, column=0, padx=10, pady=5, sticky="w")
file_types_entry = ttk.Entry(tab_converter, textvariable=converter_file_types_var, width=60)
file_types_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

ttk.Label(
    tab_converter, text="🔀 OpenCC Mode:", width=LABEL_WIDTH, anchor="w"
).grid(row=4, column=0, padx=10, pady=5, sticky="w")
opencc_mode_combo = ttk.Combobox(
    tab_converter, textvariable=opencc_mode_var, values=list(opencc_modes.keys()), state="readonly", width=60
)
opencc_mode_combo.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

ttk.Button(tab_converter, text="🚀 Start Conversion", command=converter_start_conversion).grid(row=5, column=1, pady=20, sticky="ew")
tab_converter.columnconfigure(1, weight=1)
tab_converter.rowconfigure(7, weight=1)

# 7.2 RimWorld Translator Tab
tab_translator = ttk.Frame(notebook)
notebook.add(tab_translator, text="🌍 RimWorld Translator")

translator_log_text = scrolledtext.ScrolledText(
    tab_translator, height=10, font=("Arial", 14), bg="#1E1E1E", fg="white", wrap=tk.WORD
)
translator_log_text.pack(side=tk.BOTTOM, expand=True, fill="both", padx=10, pady=10)

translator_log_text.tag_config("info", foreground="white")
translator_log_text.tag_config("warning", foreground="yellow")
translator_log_text.tag_config("error", foreground="red")
translator_log_text.tag_config("success", foreground="lightgreen")

translator_search_var = tk.StringVar()
translator_mod_folder_var = tk.StringVar()
translator_output_folder_var = tk.StringVar()
translator_output_language_var = tk.StringVar(value=output_language_options_translator[0])
translator_output_language_manual_var = tk.StringVar()
translator_placeholder_var = tk.StringVar(value=placeholder_options[0])
translator_submod_naming_var = tk.StringVar(value=submod_naming_options[2])
translator_update_mode_var = tk.StringVar(value=update_mode_options[0])

def translator_refresh_mod_list():
    mod_list = translator_list_mods()
    translator_mod_dropdown["values"] = mod_list
    translator_search_var.set("")
    log_message(translator_log_text, "Mod list refreshed.", "info")

def translator_select_mod_folder():
    global rimworld_mods_path
    new_path = filedialog.askdirectory(title="Select Mods Folder")
    if new_path:
        rimworld_mods_path = new_path
        log_message(translator_log_text, f"Selected Mods Folder: {rimworld_mods_path}", "info")
        translator_refresh_mod_list()

def translator_open_workshop_page():
    selected_mod = translator_mod_folder_var.get().split(" - ")[0]
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={selected_mod}"
    webbrowser.open(url)

def translator_open_mod_folder():
    selected_mod = translator_mod_folder_var.get().split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, selected_mod)
    if os.path.exists(mod_path):
        os.startfile(mod_path)  # On Windows
    else:
        messagebox.showerror("Error", "Mod folder not found.")

def translator_update_output_folder_display():
    selected = translator_mod_folder_var.get()
    if not selected:
        return
    mod_id = selected.split(" - ")[0]
    mod_path = os.path.join(rimworld_mods_path, mod_id)
    chosen_lang = translator_output_language_var.get()
    if chosen_lang == "Manual":
        chosen_lang = translator_output_language_manual_var.get().strip() or "English"
    translator_output_folder_var.set(os.path.join(mod_path, "Languages", chosen_lang))

def translator_on_mod_selected(*_):
    translator_update_output_folder_display()

def translator_on_language_selected(_=None):
    if translator_output_language_var.get() == "Manual":
        translator_output_language_manual_entry.config(state="normal")
    else:
        translator_output_language_manual_entry.config(state="disabled")
    translator_update_output_folder_display()

def clear_translator_log():
    translator_log_text.delete("1.0", tk.END)

def reset_conflict_choice():
    global conflict_resolution_global
    conflict_resolution_global = None
    log_message(translator_log_text, "Conflict resolution choice reset.", "info")

translator_top_frame = ttk.Frame(tab_translator, padding=10)
translator_top_frame.pack(side=tk.TOP, fill="x")

ttk.Label(translator_top_frame, text="📁 Mods Folder:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=0, sticky="w")
translator_mod_folder_var_display = tk.StringVar(value=rimworld_mods_path)
ttk.Entry(translator_top_frame, textvariable=translator_mod_folder_var_display, width=60, state="readonly")\
    .grid(column=1, row=0, padx=(10, 0), sticky="ew")
ttk.Button(translator_top_frame, text="Browse", command=translator_select_mod_folder)\
    .grid(column=2, row=0, padx=5)
translator_top_frame.columnconfigure(1, weight=1)

search_frame = ttk.Frame(tab_translator, padding=10)
search_frame.pack(side=tk.TOP, fill="x")

ttk.Label(search_frame, text="🔍 Search Mod:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=0, sticky="w")
translator_search_entry = ttk.Entry(search_frame, textvariable=translator_search_var, width=70)
translator_search_entry.grid(column=1, row=0, padx=(10, 0), sticky="ew")
translator_search_var.trace_add("write", filter_mod_list)

ttk.Label(search_frame, text="📂 Select Mod:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=1, sticky="w")
translator_mod_dropdown = ttk.Combobox(search_frame, textvariable=translator_mod_folder_var, values=[], state="readonly", width=70)
translator_mod_dropdown.grid(column=1, row=1, padx=(10, 0), sticky="ew")
translator_mod_dropdown["values"] = translator_list_mods()
translator_mod_dropdown.bind("<<ComboboxSelected>>", translator_on_mod_selected)
search_frame.columnconfigure(1, weight=1)

lang_frame = ttk.Frame(tab_translator, padding=10)
lang_frame.pack(side=tk.TOP, fill="x")

ttk.Label(lang_frame, text="🌐 Output Language:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=0, sticky="w")
translator_output_language_combo = ttk.Combobox(
    lang_frame,
    textvariable=translator_output_language_var,
    values=output_language_options_translator,
    state="readonly",
    width=60
)
translator_output_language_combo.grid(column=1, row=0, padx=(10, 0), sticky="ew")
translator_output_language_combo.bind("<<ComboboxSelected>>", translator_on_language_selected)

translator_output_language_manual_entry = ttk.Entry(
    lang_frame, textvariable=translator_output_language_manual_var, state="disabled", width=30
)
translator_output_language_manual_entry.grid(column=2, row=0, padx=(10, 0), sticky="ew")
lang_frame.columnconfigure(1, weight=1)

out_frame = ttk.Frame(tab_translator, padding=10)
out_frame.pack(side=tk.TOP, fill="x")

ttk.Label(out_frame, text="📁 Output Folder:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=0, sticky="w")
translator_output_folder_entry = ttk.Entry(out_frame, textvariable=translator_output_folder_var, width=60)
translator_output_folder_entry.grid(column=1, row=0, padx=(10, 0), sticky="ew")
out_frame.columnconfigure(1, weight=1)

ph_frame = ttk.Frame(tab_translator, padding=10)
ph_frame.pack(side=tk.TOP, fill="x")

ttk.Label(ph_frame, text="📝 Placeholder Mode:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=0, sticky="w")
translator_placeholder_combo = ttk.Combobox(
    ph_frame, textvariable=translator_placeholder_var, values=placeholder_options, state="readonly", width=60
)
translator_placeholder_combo.grid(column=1, row=0, padx=(10, 0), sticky="ew")

ttk.Label(ph_frame, text="🔤 Sub-Mod Naming Option:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=1, sticky="w")
translator_submod_naming_combo = ttk.Combobox(
    ph_frame, textvariable=translator_submod_naming_var, values=submod_naming_options, state="readonly", width=60
)
translator_submod_naming_combo.grid(column=1, row=1, padx=(10, 0), sticky="ew")

ttk.Label(ph_frame, text="🔄 Update Mode:", width=LABEL_WIDTH, anchor="w")\
    .grid(column=0, row=2, sticky="w")
translator_update_mode_combo = ttk.Combobox(
    ph_frame, textvariable=translator_update_mode_var, values=update_mode_options, state="readonly", width=60
)
translator_update_mode_combo.grid(column=1, row=2, padx=(10, 0), sticky="ew")
ph_frame.columnconfigure(1, weight=1)

btn_frame = ttk.Frame(tab_translator, padding=10)
btn_frame.pack(side=tk.TOP, fill="x")
for i in range(8):  # We now have 8 columns, including our new toggle button
    btn_frame.columnconfigure(i, weight=1)

ttk.Button(btn_frame, text="Refresh Mod List", command=translator_refresh_mod_list, width=20)\
    .grid(column=0, row=0, padx=5)
ttk.Button(btn_frame, text="Open Workshop Page", command=translator_open_workshop_page, width=20)\
    .grid(column=1, row=0, padx=5)
ttk.Button(btn_frame, text="Open Mod Folder", command=translator_open_mod_folder, width=20)\
    .grid(column=2, row=0, padx=5)
ttk.Button(btn_frame, text="Compare", command=translator_deep_compare_extraction, width=20)\
    .grid(column=3, row=0, padx=5)
ttk.Button(btn_frame, text="Extract", command=translator_extract_translation, width=20)\
    .grid(column=4, row=0, padx=5)
ttk.Button(btn_frame, text="Clear Log", command=clear_translator_log, width=20)\
    .grid(column=5, row=0, padx=5)
ttk.Button(btn_frame, text="Reset Conflict Choice", command=reset_conflict_choice, width=20)\
    .grid(column=6, row=0, padx=5)

# New button to toggle ENABLE_DETAILED_FILE_LOGS
def toggle_detailed_logs():
    global ENABLE_DETAILED_FILE_LOGS
    ENABLE_DETAILED_FILE_LOGS = not ENABLE_DETAILED_FILE_LOGS
    status = "ENABLED" if ENABLE_DETAILED_FILE_LOGS else "DISABLED"
    log_message(translator_log_text, f"Detailed file logs are now {status}.", "info")

ttk.Button(btn_frame, text="Toggle Detailed Logs", command=toggle_detailed_logs, width=20)\
    .grid(column=7, row=0, padx=5)

# ------------------------------
# 8. MAIN LOOP
# ------------------------------
try:
    root.mainloop()
except ExtractionCancelledException:
    messagebox.showinfo("Extraction Cancelled", "The extraction was cancelled by the user.")

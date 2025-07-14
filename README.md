# RimWorld Translate Helper: Complete User Guide
**Version: 1.0**

## Feature Overview

### 🈯 OpenCC Converter (Converter Tab)
Batch convert files (.txt, .xml, etc.) between Traditional and Simplified Chinese using multiple OpenCC conversion modes.

### 🌍 RimWorld Translator (Translator Tab)
Extract original text from RimWorld mod files (Defs, Keyed, etc.) and generate or merge XML translation files. Supports placeholder configuration (e.g., TODO or Original), submodule naming options, update modes (Merge/Replace), and conflict resolution.
Includes a Compare function for simulated extraction and difference checking between translated files and newly generated content.

---

## Table of Contents
- System Requirements & Prerequisites
- Feature Summary
- OpenCC Converter
- Translator Extractor
- Step-by-Step Instructions
- Toggle Detailed Logs
- How to Handle File Conflicts
- Frequently Asked Questions (FAQ)
- Packaging as EXE & Deployment
- Possible Error Handling

---

## System Requirements & Prerequisites
- Python 3.7 or higher
- Windows platform only

---

## Main Features Overview

### 📜 OpenCC Converter
**Function:**
Batch convert all text files in a folder (default: .txt, .xml) between Traditional ↔ Simplified Chinese using selected OpenCC modes.

**Key Input Fields:**
- **Input Folder**: Folder containing the original files.
- **Output Folder**: Destination folder for converted files.
- **Output Language Folder**: When operating under RimWorld’s Languages/ directory, this helps auto-fill the final language subfolder.
- **File Types**: Comma-separated file extensions to include.
- **OpenCC Mode**: Select an OpenCC conversion config (e.g., s2t.json, t2s.json, etc.).

---

### 🌍 Translator Extractor
**Function:**
Extracts Defs/Keyed strings from installed RimWorld mods and generates corresponding XML translation files.
Supports merging or replacing existing translations, handles submodules automatically, and offers detailed conflict resolution strategies.

**Key Input Fields:**
- **Mods Folder**: Path to RimWorld Workshop mods (default: ...\steamapps\workshop\content\294100).
- **Output Language**: Choose or enter the language subfolder (e.g., ChineseTraditional, ChineseSimplified, or custom via Manual).
- **Placeholder Mode**: If untranslated, fill with TODO or copy from Original.
- **Sub-Mod Naming Option**: Add a prefix or suffix to submodule translation files (default: Suffix).
- **Update Mode**:
  - Merge: Merge into existing translation files.
  - Replace: Clear old files and regenerate (recommended for redoing translations).
- **Conflict Resolution**: Choose between Merge, Prefix, Suffix, Skip, or Cancel Extraction when duplicate files are detected.

---

## Step-by-Step Instructions

### 📜 OpenCC Converter
1. Go to the 📜 OpenCC Converter tab after launching the app.
2. Enter the Input Folder and Output Folder, and select your desired OpenCC Mode.
3. Click 🚀 Start Conversion to begin batch conversion.

### 🌍 Translator Extractor
1. Switch to the 🌍 RimWorld Translator tab.
2. Ensure Mods Folder path is correct. If not, click Browse to locate your RimWorld Workshop directory.
3. Use the search bar to find a mod, or select it directly from the Select Mod dropdown.
4. Set the Output Language, Placeholder Mode, Sub-Mod Naming Option, and Update Mode.
5. Click Extract to start the extraction process.
   - To simulate extraction and view differences before applying changes, click Compare.

---

## Toggle Detailed Logs
- In the Translator Tab, use the Toggle Detailed Logs button (bottom-right) to enable/disable file-level log output.
- Default is ENABLED. If you experience lag due to large log size, click to DISABLE it.

---

## Handling File Conflicts
If a file with the same name already exists, a File Conflict prompt will appear during extraction:

- Merge: Merge new content into the existing XML file.
- Prefix/Suffix: Rename the new file and keep both (useful for overlapping submodules).
- Skip: Skip this file.
- Cancel Extraction: Abort the entire process.

You can also tick Apply to all to reuse the same decision for subsequent conflicts.

---

## Frequently Asked Questions (FAQ)

**Q: Why does nothing happen after clicking “Extract”?**
A:
- Verify the Mods Folder path is correct.
- Ensure a valid mod is selected from Select Mod.
- Check if the selected mod contains Defs or About/About.xml.

**Q: Why is the merged result not as expected?**
A:
- If Update Mode is Merge, existing non-TODO lines will be preserved.
- To regenerate all translations, switch to Replace.
- You can also use Compare to preview changes.

**Q: Why is the Output Folder not updated in “Manual” mode?**
A:
- After typing into Output Language Folder, the Output Folder should auto-update.
- If it doesn’t, try switching tabs or re-entering the field.

**Q: Logs are slowing down the app. What can I do?**
A:
- Click Toggle Detailed Logs to disable detailed logging.

**Q: What does “Extraction Cancelled” mean?**
A:
- It means the user pressed Cancel Extraction in the file conflict dialog, or an unexpected interruption occurred.

---

## Packaging as EXE & Deployment
*(Not detailed in current document; assumed knowledge of PyInstaller or similar tools.)*

---

## Possible Error Handling

**Cannot read About.xml**
- Some mods may have incomplete structures. Ensure the About folder contains a valid About.xml.

**OpenCC Mode Error**
- If the OpenCC library is missing or the mode file is not found, an initialization error will appear.
- Double-check the opencc_modes mapping and your installation.

**Selected wrong conflict option**
- Click Reset Conflict Choice to clear the current conflict handling rule. You’ll be prompted again on the next conflict.

# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# --- Determine Data Files ---
# Collect all files from templates and static directories
def get_data_files(src_dir_name):
    data_files = []
    src_dir = Path(src_dir_name)
    if src_dir.is_dir():
        for item in src_dir.rglob('*'):
            if item.is_file():
                # Destination path relative to the source directory name
                dest_path = Path(src_dir_name) / item.relative_to(src_dir)
                data_files.append((str(item), str(dest_path.parent)))
    else:
         print(f"Warning: Source directory '{src_dir_name}' not found.")
    return data_files

datas = []
datas += get_data_files('templates')
datas += get_data_files('static')
# Add the default motivation letter template
letter_template_src = Path('motivation_letters/template/motivation_letter_template.docx')
if letter_template_src.is_file():
    datas.append((str(letter_template_src), 'motivation_letters/template'))
else:
    print(f"Warning: Letter template '{letter_template_src}' not found.")
# Add the default scraper settings (if needed at runtime by packaged app)
scraper_settings_src = Path('job-data-acquisition/settings.json')
if scraper_settings_src.is_file():
     datas.append((str(scraper_settings_src), 'job-data-acquisition'))
else:
     print(f"Warning: Scraper settings '{scraper_settings_src}' not found.")


# --- Hidden Imports ---
# List modules that PyInstaller might miss
hiddenimports = [
    'flask',
    'openai',
    'keyring.backends.Windows', # Example for Windows
    'keyring.backends.macOS',   # Example for macOS
    'keyring.backends.SecretService', # Example for Linux (SecretService)
    'keyring.backends.kwallet',     # Example for Linux (KWallet)
    'appdirs',
    'werkzeug',
    'jinja2',
    'dotenv',
    'requests',
    'bs4', # beautifulsoup4
    'fitz', # PyMuPDF
    'docxtpl',
    'docx', # python-docx
    # Add any other potentially hidden imports discovered during testing
    'pkg_resources.py2_warn', # Common hidden import issue
    'PIL', # Pillow if used by OCR or other libs
    'numpy', # If used by OCR or other libs
]

# --- Analysis ---
a = Analysis(
    ['dashboard.py'], # Main entry point script
    pathex=[], # Add paths to search for modules if needed
    binaries=[], # List any non-python binaries (.dll, .so)
    datas=datas, # Add data files (templates, static, etc.)
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[], # List modules to exclude if necessary
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- Executable ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JobsearchAI', # Name of the final executable
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True, # Use UPX for compression if available
    console=False, # False = GUI app (no console window), True = Console app
    # windowed=True, # Use instead of console=False for GUI apps
    # icon='static/icon.ico', # Path to application icon (Windows)
)

# --- Collect Files ---
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JobsearchAI', # Name of the output folder
)

# --- macOS App Bundle ---
# This part only runs on macOS
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='JobsearchAI.app', # Name of the .app bundle
        # icon='static/icon.icns', # Path to .icns file for macOS
        bundle_identifier='com.yourcompany.jobsearchai', # Reverse domain notation identifier
        # Add Info.plist settings if needed
        # info_plist={
        #     'NSPrincipalClass': 'NSApplication',
        #     'NSAppleScriptEnabled': False,
        #     'CFBundleDevelopmentRegion': 'English',
        #     # Add other keys as required
        # }
    )

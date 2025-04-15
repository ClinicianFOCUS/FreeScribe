from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Collect all PIL submodules
hiddenimports = collect_submodules('PIL')

# Collect PIL data files
datas = collect_data_files('PIL')

# Add specific Tkinter support modules
hiddenimports += [
    'PIL._tkinter_finder',
    'PIL.ImageTk',
] 
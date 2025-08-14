# hook-en_core_web_md.py
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata
import os
import en_ner_bc5cdr_md

# Collect all submodules
hiddenimports = collect_submodules('en_ner_bc5cdr_md')

# Collect all data files
datas = collect_data_files('en_ner_bc5cdr_md')

# Add metadata
datas += copy_metadata('en_ner_bc5cdr_md')

# Explicitly add the __init__.py file
model_path = os.path.dirname(en_ner_bc5cdr_md.__file__)
init_file = os.path.join(model_path, '__init__.py')
datas.append((init_file, 'en_ner_bc5cdr_md'))

# Explicitly add the package itself to hidden imports
if 'en_ner_bc5cdr_md' not in hiddenimports:
    hiddenimports.append('en_ner_bc5cdr_md')
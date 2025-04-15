# How to use this file
#
# 1. create a folder called "hooks" in your repo
# 2. copy this file there
# 3. add the --additional-hooks-dir flag to your pyinstaller command:
#    ex: `pyinstaller --name binary-name --additional-hooks-dir=./hooks entry-point.py`


from PyInstaller.utils.hooks import collect_data_files, get_package_paths, collect_dynamic_libs
import os, sys

# Get the package path
package_path = get_package_paths('llama_cpp')[0]

# Collect data files
datas = collect_data_files('llama_cpp')

# Append the additional .dll or .so file
if sys.platform == 'darwin':
    dllOrDylib = 'libllama.dylib'
elif sys.platform.startswith('linux'):
    dllOrDylib = 'libllama.so'
else:
    dllOrDylib = 'llama.dll'

dll_path = os.path.join(package_path, 'llama_cpp', 'lib', dllOrDylib)
if sys.platform.startswith('linux'):
    # Create the lib directory and place the file there
    datas.append((dll_path, os.path.join('llama_cpp', 'lib')))
    # Also collect any other dynamic libraries that might be needed
    libs = collect_dynamic_libs('llama_cpp')
    for lib in libs:
        datas.append((lib[0], os.path.join('llama_cpp', 'lib')))
else:
    datas.append((dll_path, 'llama_cpp'))

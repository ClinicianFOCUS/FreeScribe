"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2025 Braedon Hendy

Further updates and packaging added in 2024-2025 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform. 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students (Software Developers) - 
Alex Simko, Pemba Sherpa, Naitik Patel, Yogesh Kumar and Xun Zhong.
"""

import platform
import certifi
import sys
import os
from pathlib import Path
from utils.file_utils import get_file_path, get_resource_path
import psutil

# Constants
# Low memory threshold, Amount of ram that defines it low mem in bytes
LOW_MEM_THRESHOLD = 12e9  # 12 GB


def is_macos():
    """
    Check if the current system is macOS.
    
    :returns bool: True if macOS, False otherwise
    """
    
    return platform.system() == "Darwin"

def is_windows():
    """
    Check if the current system is Windows.
    
    :returns bool: True if Windows, False otherwise
    """
    
    return platform.system() == "Windows"

def is_linux():
    """
    Check if the current system is Linux.
    
    :returns bool: True if Linux, False otherwise
    """
    
    return platform.system() == "Linux"

def is_flatpak():
    return is_linux() and os.environ.get('container') == 'flatpak'

def install_macos_ssl_certificates():
    """
    Install the SSL certificates for macOS.

    This function is necessary to ensure that the requests library can make HTTPS requests on macOS.
    """
    abspath_to_certifi_cafile = os.path.abspath(certifi.where())
    os.environ['SSL_CERT_FILE'] = abspath_to_certifi_cafile
    os.environ['REQUESTS_CA_BUNDLE'] = abspath_to_certifi_cafile
    if getattr(sys, 'frozen', False):  # Check if running as a bundled app in macOS
        os.environ["PATH"] = os.path.join(sys._MEIPASS, 'ffmpeg')+ os.pathsep + os.environ["PATH"]


def set_cuda_paths():
    """
    Configure CUDA-related environment variables and paths.

    Sets up the necessary environment variables for CUDA execution when CUDA
    architecture is selected. Updates CUDA_PATH, CUDA_PATH_V12_4, and PATH
    environment variables with the appropriate NVIDIA driver paths.
    """
    nvidia_base_path = Path(get_file_path('nvidia-drivers'))

    cuda_path = nvidia_base_path / 'cuda_runtime' / 'bin'
    cublas_path = nvidia_base_path / 'cublas' / 'bin'
    cudnn_path = nvidia_base_path / 'cudnn' / 'bin'

    # Only add paths that actually exist
    paths_to_add = []
    for path in [cuda_path, cublas_path, cudnn_path]:
        if path.exists():
            paths_to_add.append(str(path))

    # Only proceed if we have valid paths to add
    if paths_to_add:
        env_vars = ['CUDA_PATH', 'CUDA_PATH_V12_4', 'PATH']

        for env_var in env_vars:
            current_value = os.environ.get(env_var, '')
            new_value = os.pathsep.join(paths_to_add + ([current_value] if current_value else []))
            os.environ[env_var] = new_value

        
def get_total_system_memory():
    """
    Get the total system memory in bytes.
    
    :returns int: Total system memory in bytes
    """
    return psutil.virtual_memory().total 

  
def is_system_low_memory():
    """
    Check if the system is in low memory mode.
    
    :returns bool: True if the system is in low memory mode, False otherwise
    """
    
    return get_total_system_memory() < LOW_MEM_THRESHOLD


def get_system_name():
    """
    Get the system name.
    """
    return platform.system()

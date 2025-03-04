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
import psutil   

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
        
def get_total_system_memory():
    """
    Get the total system memory in bytes.
    
    :returns int: Total system memory in bytes
    """
    print(psutil.virtual_memory().total)
    return psutil.virtual_memory().total 

def is_system_low_memory():
    """
    Check if the system is in low memory mode.
    
    :returns bool: True if the system is in low memory mode, False otherwise
    """
    
    return get_total_system_memory() < 9e9  # 8 GB
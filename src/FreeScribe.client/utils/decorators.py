"""
This software is released under the AGPL-3.0 license
Copyright (c) 2023-2025 Braedon Hendy

Further updates and packaging added in 2024-2025 through the ClinicianFOCUS initiative, 
a collaboration with Dr. Braedon Hendy and Conestoga College Institute of Applied 
Learning and Technology as part of the CNERG+ applied research project, 
Unburdening Primary Healthcare: An Open-Source AI Clinician Partner Platform". 
Prof. Michael Yingbull (PI), Dr. Braedon Hendy (Partner), 
and Research Students (Software Developers) - 
Alex Simko, Pemba Sherpa, Naitik Patel, Yogesh Kumar and Xun Zhong.
"""

import platform
from utils.log_config import logger


def windows_only(func):
    """Decorator to ensure a function only runs on Windows systems.

    Args:
        func: The function to be wrapped

    Returns:
        The wrapped function that only executes on Windows
    """
    def wrapper(*args, **kwargs):
        if platform.system() != "Windows":
            logger.info("This feature is only supported on Windows.")
            return
        return func(*args, **kwargs)
    return wrapper

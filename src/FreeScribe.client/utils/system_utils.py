import psutil
import GPUtil


def get_system_memory():
    """
    Gets system RAM information in GB.
    Returns:
        float: Available system RAM in GB
    """
    try:      
        # Get system RAM
        ram_gb = psutil.virtual_memory().total / (1024**3)
        return ram_gb
    except ImportError:
        # If modules not available, return a conservative estimate
        return 4  # Assume 4GB RAM

def get_system_vram():
    """
    Gets system VRAM information in GB.
    Returns:
        float: Available system VRAM in GB
    """
    try:       
        # Get VRAM (if available)
        vram_gb = 0
        try:
            gpus = GPUtil.getGPUs()
            for gpu in gpus:
                vram_gb = max(vram_gb, gpu.memoryTotal / 1024)  # Convert from MB to GB
        except Exception:
            # No GPU or GPUtil failed
            pass

        return vram_gb
    except ImportError:
        # If modules not available, return a conservative estimate
        return 0  # Assume no VRAM
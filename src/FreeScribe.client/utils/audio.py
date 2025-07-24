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

import numpy as np
from utils.AESCryptoUtils import AESCryptoUtilsClass as AESCryptoUtils
import utils.file_utils
from utils.log_config import logger
import os
import wave
import io

DEFAULT_RATE = 16000
DEFAULT_CHUNK_SIZE = 512

def pad_audio_chunk(chunk, pad_seconds=0.5, rate = DEFAULT_RATE, chunk_size = DEFAULT_CHUNK_SIZE):
    """
    Pad an audio chunk with silence at the beginning and end.
    
    Parameters
    ----------
    chunk : np.ndarray
        The audio chunk to pad.
    pad_seconds : float
        The number of seconds to pad the chunk with.

    Returns
    -------
    np.ndarray
        The padded audio chunk.
    """

    # Calculate how many chunks make up half a second
    pad_chunk_leng = int(pad_seconds * rate / chunk_size)

    # Create half a second of silence (all zeros)
    silent_chunk = np.zeros(chunk_size, dtype=np.int16).tobytes()

    # Create arrays of silent chunks
    silence_start = [silent_chunk] * pad_chunk_leng
    silence_end = [silent_chunk] * pad_chunk_leng

    return silence_start + chunk + silence_end

def encrypt_audio_chunk(chunk, filepath: str):
    """
    Encrypt an audio chunk using AES encryption and save as WAV format.
    Appends to existing file if it exists.
    
    Parameters
    ----------
    chunk : bytes or np.ndarray
        The audio chunk to encrypt.
    filepath : str, optional
        Base filename to save the encrypted file (without extension)
        If None, uses the current_recording_file from client.py
    """  
    filepath = utils.file_utils.get_resource_path(f"recordings/{filepath}.AE2")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Convert chunk to numpy array if needed
    if not isinstance(chunk, np.ndarray):
        chunk = np.frombuffer(chunk, dtype=np.int16)
    
    # Check if file exists and has content
    existing_data = None
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        try:
            with open(filepath, 'rb') as f:
                encrypted_data = f.read()
                existing_data = AESCryptoUtils.decrypt_bytes(encrypted_data)
        except Exception as e:
            logger.exception(f"Error reading existing file {filepath}: {str(e)}")
            existing_data = None
    
    # Create in-memory WAV file combining existing and new data
    with io.BytesIO() as wav_buffer:
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(DEFAULT_RATE)
            
            # Write existing frames if they exist
            if existing_data:
                with io.BytesIO(existing_data) as existing_buffer:
                    with wave.open(existing_buffer, 'rb') as existing_wav:
                        wav_file.writeframes(existing_wav.readframes(existing_wav.getnframes()))
            
            # Write new frames
            wav_file.writeframes(chunk.tobytes())
        
        # Encrypt the combined WAV data
        encrypted_data = AESCryptoUtils.encrypt_bytes(wav_buffer.getvalue())
        
        # Write encrypted data to file
        with open(filepath, 'wb') as f:
            f.write(encrypted_data)
        
        logger.info(f"Encrypted audio saved to {filepath} (appended: {len(chunk)} samples)")

def decrypt_whole_audio_file(filename: str):
    """
    Decrypt an encrypted audio file and save as WAV.
    
    Parameters
    ----------
    filename : str
        Base filename of the encrypted file (without extension)
        
    Returns
    -------
    np.ndarray
        The decrypted audio data
    """
    filepath = utils.file_utils.get_resource_path(f"recordings/{filename}")
    
    try:
        # Read encrypted data
        with open(filepath, 'rb') as f:
            encrypted_data = f.read()
            
        if not encrypted_data:
            logger.warning(f"Empty encrypted file: {filepath}")
            return np.array([], dtype=np.int16)
        
        # Decrypt data
        decrypted_data = AESCryptoUtils.decrypt_bytes(encrypted_data)
        
        # Validate decrypted WAV data
        if not decrypted_data or len(decrypted_data) < 44:  # Minimum WAV header size
            logger.warning(f"Invalid WAV data in file: {filepath}")
            return np.array([], dtype=np.int16)
        
        # Write decrypted WAV data to file
        wav_buffer = io.BytesIO()
        wav_buffer.write(decrypted_data)
        wav_buffer.seek(0)
            
        # Read WAV file to get numpy array
        with wave.open(wav_buffer, 'rb') as wav_file:
            n_frames = wav_file.getnframes()
            if n_frames == 0:
                logger.warning(f"Empty audio file: {wav_buffer}")
                return np.array([], dtype=np.int16)
            frames = wav_file.readframes(n_frames)
            wav_data = np.frombuffer(frames, dtype=np.int16)
            
        logger.info(f"Successfully decrypted audio with {len(wav_data)} samples.")
        return wav_data
        
    except FileNotFoundError:
        logger.exception(f"File not found: {filepath}")
        raise
    except wave.Error as e:
        logger.exception(f"Invalid WAV file format: {str(e)}")
        return np.array([], dtype=np.int16)
    except Exception as e:
        logger.exception(f"Error decrypting audio: {str(e)}")
        raise

import keyring
import base64
import os
import secrets
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
   
class AESCryptoUtilsClass:
    """Utility class for AES encryption and decryption using keys stored in Windows Credential Manager"""
    
    # Constants for credential storage
    SERVICE_NAME = "FreeScribe"
    KEY_USERNAME = "aes_encryption_key"
    
    @classmethod
    def _ensure_key_exists(cls):
        """Ensure AES encryption key exists in the credential manager, create if not present"""
        # Check for AES key
        aes_key = keyring.get_password(cls.SERVICE_NAME, cls.KEY_USERNAME)
        if not aes_key:
            # Generate a secure 256-bit (32 bytes) key for AES-256 and store it
            aes_key = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
            keyring.set_password(cls.SERVICE_NAME, cls.KEY_USERNAME, aes_key)
    
    @classmethod
    def _get_aes_key(cls):
        """Retrieve or create AES encryption key from Windows Credential Manager"""
        cls._ensure_key_exists()
        
        # Get stored key
        aes_key = keyring.get_password(cls.SERVICE_NAME, cls.KEY_USERNAME)
        
        # Decode from storage format
        return base64.urlsafe_b64decode(aes_key)
        
    @classmethod
    def encrypt(cls, plaintext):
        """
        Encrypt the given plaintext using AES-256 with the stored encryption key
        
        Args:
            plaintext (str): Text to encrypt
            
        Returns:
            str: Base64-encoded encrypted data (includes IV + ciphertext)
        """
        if not plaintext:
            return ""
            
        try:
            key = cls._get_aes_key()
            
            # Convert plaintext to bytes if it's a string
            if isinstance(plaintext, str):
                plaintext = plaintext.encode('utf-8')
            
            # Generate a random 16-byte initialization vector
            iv = secrets.token_bytes(16)
            
            # Create a padder to ensure the plaintext length is a multiple of block size
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(plaintext) + padder.finalize()
            
            # Create an encryptor with AES in CBC mode
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            
            # Encrypt the padded data
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and ciphertext and encode as base64
            return base64.urlsafe_b64encode(iv + ciphertext).decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"AES encryption failed: {str(e)}") from e
    
    @classmethod
    def decrypt(cls, encrypted_text):
        """
        Decrypt the given AES-encrypted text using the stored encryption key
        
        Args:
            encrypted_text (str): Base64-encoded encrypted data (IV + ciphertext)
            
        Returns:
            str: Decrypted plaintext
        """
        if not encrypted_text:
            return ""
            
        try:
            key = cls._get_aes_key()
            
            # Decode the encrypted data from base64
            encrypted_data = base64.urlsafe_b64decode(encrypted_text)
            
            # Extract IV (first 16 bytes) and ciphertext
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            
            # Create a decryptor with AES in CBC mode
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            
            # Decrypt the ciphertext
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
            
            # Convert bytes to string
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"AES decryption failed: {str(e)}") from e

    @classmethod
    def encrypt_bytes(cls, plaintext_bytes):
        """
        Encrypt the given bytes using AES-256 with the stored encryption key
        
        Args:
            plaintext_bytes (bytes): Bytes to encrypt
            
        Returns:
            bytes: Encrypted data (IV + ciphertext)
        """
        if not plaintext_bytes:
            return b""
            
        try:
            key = cls._get_aes_key()
            
            # Generate a random 16-byte initialization vector
            iv = secrets.token_bytes(16)
            
            # Create a padder to ensure the plaintext length is a multiple of block size
            padder = padding.PKCS7(algorithms.AES.block_size).padder()
            padded_data = padder.update(plaintext_bytes) + padder.finalize()
            
            # Create an encryptor with AES in CBC mode
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            encryptor = cipher.encryptor()
            
            # Encrypt the padded data
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and ciphertext
            
            return iv + ciphertext
            
        except Exception as e:
            raise ValueError(f"AES encryption failed: {str(e)}") from e
    
    @classmethod
    def decrypt_bytes(cls, encrypted_bytes):
        """
        Decrypt the given AES-encrypted bytes using the stored encryption key
        
        Args:
            encrypted_bytes (bytes): Encrypted data (IV + ciphertext)
            
        Returns:
            bytes: Decrypted plaintext
        """
        if not encrypted_bytes:
            return b""
            
        try:
            key = cls._get_aes_key()
            
            # Extract IV (first 16 bytes) and ciphertext
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # Create a decryptor with AES in CBC mode
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            
            # Decrypt the ciphertext
            padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Remove padding
            unpadder = padding.PKCS7(algorithms.AES.block_size).unpadder()
            plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
            
            return plaintext
            
        except Exception as e:
            raise ValueError(f"AES decryption failed: {str(e)}") from e
    
    @classmethod
    def change_encryption_key(cls):
        """Generate and store a new AES encryption key"""
        # Generate new 256-bit key for AES-256
        new_key = base64.urlsafe_b64encode(os.urandom(32)).decode('utf-8')
        
        # Update stored key
        keyring.set_password(cls.SERVICE_NAME, cls.KEY_USERNAME, new_key)
        
        return True

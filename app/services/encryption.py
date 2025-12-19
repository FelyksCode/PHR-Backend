"""
Encryption utilities for securely storing OAuth tokens
"""
from cryptography.fernet import Fernet
from app.config import settings
import base64


class TokenEncryption:
    """
    Handles encryption and decryption of OAuth tokens using Fernet (symmetric encryption)
    """
    
    def __init__(self):
        """
        Initialize encryption with key from settings
        Raises ValueError if encryption key is not configured
        """
        if not settings.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY must be set in environment variables. "
                "Generate one using: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        
        # Ensure the key is properly formatted
        try:
            key = settings.encryption_key.encode() if isinstance(settings.encryption_key, str) else settings.encryption_key
            self.cipher = Fernet(key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {str(e)}")
    
    def encrypt(self, data: str) -> str:
        """
        Encrypt a string
        
        Args:
            data: Plain text string to encrypt
            
        Returns:
            Encrypted string (base64 encoded)
        """
        if not data:
            return ""
        
        encrypted_bytes = self.cipher.encrypt(data.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            encrypted_data: Encrypted string (base64 encoded)
            
        Returns:
            Decrypted plain text string
        """
        if not encrypted_data:
            return ""
        
        decrypted_bytes = self.cipher.decrypt(encrypted_data.encode())
        return decrypted_bytes.decode()


# Global instance
token_encryption = TokenEncryption()

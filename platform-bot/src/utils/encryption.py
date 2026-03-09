"""
Encryption utilities for securing sensitive data
Bot tokens, API keys, etc.
"""
import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class TokenEncryption:
    """
    Encrypts and decrypts sensitive tokens using Fernet symmetric encryption

    Usage:
        # Initialize with key
        encryptor = TokenEncryption(key=b'your-32-byte-key...')

        # Encrypt token
        encrypted = encryptor.encrypt('123456:ABC-DEF...')

        # Decrypt token
        decrypted = encryptor.decrypt(encrypted)
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize encryption with a key

        Args:
            key: 32-byte encryption key. If None, generates new key.
        """
        if key is None:
            # Generate random key
            self.key = Fernet.generate_key()
        else:
            # Ensure key is proper length for Fernet (base64 encoded 32 bytes)
            if len(key) < 32:
                # Derive key from shorter key using PBKDF2HMAC
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'bot_saas_salt',  # In production, use random salt per application
                    iterations=100000,
                )
                derived_key = kdf.derive(key)
                self.key = base64.urlsafe_b64encode(derived_key)
            elif len(key) == 44 and key.count(b'=') == 1:
                # Already a valid Fernet key
                self.key = key
            else:
                # Use PBKDF2HMAC to create proper Fernet key
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'bot_saas_salt',
                    iterations=100000,
                )
                derived_key = kdf.derive(key[:32])
                self.key = base64.urlsafe_b64encode(derived_key)

        self.fernet = Fernet(self.key)

    def encrypt(self, token: str) -> str:
        """
        Encrypt a token string

        Args:
            token: Plain text token to encrypt

        Returns:
            Encrypted token as string (base64 encoded)

        Raises:
            ValueError: If token is empty or not a string
        """
        if not token:
            raise ValueError("Token cannot be empty")

        if not isinstance(token, str):
            raise ValueError("Token must be a string")

        # Convert to bytes if needed
        token_bytes = token.encode('utf-8')

        # Encrypt
        encrypted_bytes = self.fernet.encrypt(token_bytes)

        # Return as string
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, encrypted_token: str) -> str:
        """
        Decrypt an encrypted token

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Decrypted plain text token

        Raises:
            ValueError: If token is empty or decryption fails
        """
        if not encrypted_token:
            raise ValueError("Encrypted token cannot be empty")

        try:
            # Convert to bytes
            encrypted_bytes = encrypted_token.encode('utf-8')

            # Decrypt
            decrypted_bytes = self.fernet.decrypt(encrypted_bytes)

            # Return as string
            return decrypted_bytes.decode('utf-8')

        except Exception as e:
            raise ValueError(f"Failed to decrypt token: {e}")

    def rotate_key(self, new_key: bytes) -> None:
        """
        Rotate to a new encryption key

        In production, you would need to re-encrypt all existing tokens
        with the new key.

        Args:
            new_key: New encryption key
        """
        self.key = new_key
        self.fernet = Fernet(self.key)

    @staticmethod
    def generate_key() -> bytes:
        """
        Generate a new Fernet key

        Returns:
            Base64 encoded 32-byte key suitable for Fernet
        """
        return Fernet.generate_key()

    @staticmethod
    def key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive encryption key from password using PBKDF2

        Args:
            password: Password to derive key from
            salt: Salt for key derivation (optional)

        Returns:
            Base64 encoded Fernet key
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )

        derived_key = kdf.derive(password.encode('utf-8'))
        return base64.urlsafe_b64encode(derived_key)


# Global encryption instance
_encryptor: Optional[TokenEncryption] = None


def get_encryptor(key: Optional[bytes] = None) -> TokenEncryption:
    """
    Get global encryption instance (singleton)

    Args:
        key: Encryption key. Only used on first call.

    Returns:
        TokenEncryption instance
    """
    global _encryptor
    if _encryptor is None:
        _encryptor = TokenEncryption(key)
    return _encryptor


def encrypt_token(token: str, key: Optional[bytes] = None) -> str:
    """
    Encrypt a bot token

    Args:
        token: Plain text bot token
        key: Optional encryption key

    Returns:
        Encrypted token
    """
    encryptor = get_encryptor(key)
    return encryptor.encrypt(token)


def decrypt_token(encrypted_token: str, key: Optional[bytes] = None) -> str:
    """
    Decrypt a bot token

    Args:
        encrypted_token: Encrypted token
        key: Optional encryption key

    Returns:
        Decrypted plain text token
    """
    encryptor = get_encryptor(key)
    return encryptor.decrypt(encrypted_token)


def generate_encryption_key() -> str:
    """
    Generate a new encryption key for .env file

    Returns:
        Base64 encoded encryption key
    """
    return TokenEncryption.generate_key().decode('utf-8')

#!/usr/bin/env python3
"""
Generate secure secrets for production deployment
"""

import secrets
import string
import base64
from cryptography.fernet import Fernet


def generate_password(length=32):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_jwt_secret():
    """Generate a secure JWT secret key"""
    return secrets.token_urlsafe(64)


def generate_encryption_key():
    """Generate a Fernet encryption key"""
    return Fernet.generate_key().decode()


def generate_webhook_secret():
    """Generate a webhook secret"""
    return secrets.token_urlsafe(32)


if __name__ == "__main__":
    print("=" * 70)
    print("SECURE SECRETS GENERATOR FOR TELEGRAM BOT SAAS")
    print("=" * 70)
    print()

    print("🔐 POSTGRES_PASSWORD:")
    print(f"   {generate_password()}")
    print()

    print("🔐 REDIS_PASSWORD:")
    print(f"   {generate_password()}")
    print()

    print("🔐 ENCRYPTION_KEY (Fernet):")
    print(f"   {generate_encryption_key()}")
    print()

    print("🔐 JWT_SECRET_KEY:")
    print(f"   {generate_jwt_secret()}")
    print()

    print("🔐 PLATFORM_BOT_WEBHOOK_SECRET:")
    print(f"   {generate_webhook_secret()}")
    print()

    print("=" * 70)
    print("⚠️  Copy these values to your .env.prod file")
    print("⚠️  Keep these secrets secure and never commit to git!")
    print("=" * 70)

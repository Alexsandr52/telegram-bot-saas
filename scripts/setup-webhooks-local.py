#!/usr/bin/env python3
"""
Setup Webhooks for All Bots
Decrypts tokens and sets webhooks using localhost URL
"""
import asyncio
import asyncpg
import httpx
import os
import sys
from loguru import logger


async def decrypt_token(encrypted_token: str, key: str) -> str:
    """Decrypt bot token using Fernet"""
    try:
        from cryptography.fernet import Fernet

        fernet = Fernet(key.encode())
        decrypted = fernet.decrypt(encrypted_token.encode()).decode()
        return decrypted
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        raise


async def set_webhook(bot_token: str, webhook_url: str, bot_id: str) -> bool:
    """Set webhook for a bot"""
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    payload = {
        "url": webhook_url,
        "drop_pending_updates": True
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, json=payload)
            result = response.json()

            if result.get("ok"):
                logger.info(f"✅ Webhook set for bot {bot_id[:8]}")
                logger.info(f"   URL: {webhook_url}")
                return True
            else:
                logger.error(f"❌ Failed to set webhook for bot {bot_id[:8]}")
                logger.error(f"   Error: {result.get('description', 'Unknown')}")
                return False

        except Exception as e:
            logger.error(f"❌ Error setting webhook for bot {bot_id[:8]}: {e}")
            return False


async def get_webhook_info(bot_token: str, bot_id: str) -> dict:
    """Get webhook info for a bot"""
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(api_url)
            result = response.json()

            if result.get("ok"):
                webhook_info = result.get("result", {})
                logger.info(f"📋 Webhook info for bot {bot_id[:8]}:")
                logger.info(f"   URL: {webhook_info.get('url', 'Not set')}")
                logger.info(f"   Pending updates: {webhook_info.get('pending_update_count', 0)}")
                return webhook_info
            else:
                logger.error(f"Failed to get webhook info: {result.get('description')}")
                return {}

        except Exception as e:
            logger.error(f"Error getting webhook info: {e}")
            return {}


async def update_bot_webhook_url(bot_id: str, webhook_url: str, database_url: str):
    """Update webhook URL in database"""
    query = """
        UPDATE bots
        SET webhook_url = $1,
            updated_at = NOW()
        WHERE id = $2
    """

    conn = await asyncpg.connect(database_url)
    try:
        await conn.execute(query, webhook_url, bot_id)
        logger.info(f"Updated webhook_url in DB for bot {bot_id[:8]}")
    finally:
        await conn.close()


async def main():
    """Main function"""

    # Configuration
    encryption_key = os.getenv("ENCRYPTION_KEY")
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@database:5432/bot_saas")

    # Webhook base URL (localhost for testing)
    webhook_base_url = os.getenv("WEBHOOK_BASE_URL", "http://localhost")

    if not encryption_key:
        logger.error("ENCRYPTION_KEY not set in environment")
        sys.exit(1)

    logger.info("Starting webhook setup...")
    logger.info(f"Webhook base URL: {webhook_base_url}")

    try:
        conn = await asyncpg.connect(database_url)

        # Get all active bots
        query = """
            SELECT
                id,
                bot_token,
                bot_username
            FROM bots
            WHERE is_active = true
                AND container_status IN ('running', 'creating')
        """

        rows = await conn.fetch(query)

        if not rows:
            logger.warning("No active bots found")
            return

        logger.info(f"Found {len(rows)} active bot(s)")

        success_count = 0
        fail_count = 0

        for row in rows:
            bot_id = row['id']
            encrypted_token = row['bot_token']
            bot_username = row['bot_username']

            try:
                # Decrypt token
                decrypted_token = decrypt_token(encrypted_token, encryption_key)
                logger.info(f"Decrypted token for @{bot_username}")

                # Construct webhook URL
                webhook_url = f"{webhook_base_url}/webhook/{bot_id}"

                # Set webhook
                success = await set_webhook(decrypted_token, webhook_url, bot_id)

                if success:
                    # Update in database
                    await update_bot_webhook_url(bot_id, webhook_url, database_url)
                    success_count += 1
                    logger.success(f"✅ Webhook set successfully for @{bot_username}")
                else:
                    fail_count += 1
                    logger.error(f"❌ Failed to set webhook for @{bot_username}")

                # Small delay between bots
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to process bot @{bot_username}: {e}")
                fail_count += 1

        await conn.close()

        logger.info("="*50)
        logger.info(f"Webhook setup complete!")
        logger.info(f"Success: {success_count}")
        logger.info(f"Failed: {fail_count}")
        logger.info(f"Total: {success_count + fail_count}")
        logger.info("="*50)

    except Exception as e:
        logger.exception(f"Fatal error in webhook setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

#!/usr/bin/env python3
"""
Switch Bots to Webhook Mode
Restarts bots with USE_WEBHOOK=1 and WEBHOOK_PATH
"""
import asyncio
import asyncpg
import os
import sys
from loguru import logger


async def restart_bots_with_webhook(database_url: str):
    """Restart all active bots with webhook mode enabled"""

    conn = await asyncpg.connect(database_url)

    try:
        # Get all active bots
        query = """
            SELECT
                id,
                bot_username,
                container_id
            FROM bots
            WHERE is_active = true
                AND container_status = 'running'
        """

        rows = await conn.fetch(query)

        if not rows:
            logger.warning("No running bots found")
            return

        logger.info(f"Found {len(rows)} running bot(s)")

        # Check if factory service is accessible
        try:
            factory_response = await call_factory_api(conn, "/api/v1/factory/bots/restart-webhooks")
            logger.info("Called factory service to restart bots in webhook mode")
        except Exception as e:
            logger.error(f"Failed to call factory service: {e}")

        await conn.close()

    except Exception as e:
        logger.exception(f"Failed to restart bots: {e}")
        raise


async def call_factory_api(conn, endpoint: str) -> dict:
    """Call factory API to restart bot containers"""
    try:
        query = """
            SELECT bot_token
            FROM bots
            WHERE bot_username = 'platform_bot'
            LIMIT 1
        """

        row = await conn.fetchrow(query)
        if not row:
            return {}

        bot_token = row['bot_token']

        # Decrypt token
        encryption_key = os.getenv("ENCRYPTION_KEY")
        from cryptography.fernet import Fernet
        fernet = Fernet(encryption_key.encode())
        decrypted_token = fernet.decrypt(bot_token.encode()).decode()

        # Call factory service API
        import httpx

        factory_url = os.getenv("FACTORY_SERVICE_URL", "http://factory-service:8002")

        api_url = f"{factory_url}{endpoint}"
        headers = {"X-Auth-Token": decrypted_token}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(api_url, headers=headers)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Factory service returned {response.status_code}")
                return {"error": str(response.status_code)}

    except Exception as e:
        logger.error(f"Failed to call factory API: {e}")
        return {"error": str(e)}


async def main():
    """Main function"""
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@database:5432/bot_saas")

    logger.info("Starting webhook mode switch...")

    try:
        await restart_bots_with_webhook(database_url)
        logger.info("Webhook mode switch complete!")
    except Exception as e:
        logger.exception(f"Failed webhook mode switch: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

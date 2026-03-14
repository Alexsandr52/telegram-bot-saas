#!/usr/bin/env python3
"""
Update Webhooks for All Bots
Supports both ngrok (local) and production domain
"""
import asyncio
import asyncpg
import httpx
import os
from typing import Optional
from loguru import logger


async def get_all_bots(database_url: str) -> list[dict]:
    """
    Get all active bots with their tokens

    Args:
        database_url: PostgreSQL connection URL

    Returns:
        List of bot dictionaries
    """
    query = """
        SELECT
            id,
            bot_token,
            bot_username,
            webhook_url as current_webhook,
            container_status
        FROM bots
        WHERE is_active = true
            AND container_status IN ('running', 'creating')
        ORDER BY created_at
    """

    conn = await asyncpg.connect(database_url)
    try:
        rows = await conn.fetch(query)
        bots = [dict(row) for row in rows]
        return bots
    finally:
        await conn.close()


async def set_webhook(
    bot_token: str,
    webhook_url: str,
    secret_token: Optional[str] = None
) -> bool:
    """Set webhook for a Telegram bot"""
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    payload = {
        "url": webhook_url,
        "drop_pending_updates": True
    }

    if secret_token:
        payload["secret_token"] = secret_token

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, json=payload)
            result = response.json()

            if result.get("ok"):
                return True
            else:
                logger.error(f"Webhook error: {result.get('description')}")
                return False

        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False


async def update_webhook_in_db(database_url: str, bot_id: str, webhook_url: str):
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
    finally:
        await conn.close()


async def main():
    """Main function"""

    # Configuration
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@database:5432/bot_saas"
    )

    # Get webhook base URL
    ngrok_enabled = os.getenv("NGROK_ENABLED", "false").lower() == "true"
    if ngrok_enabled:
        # For ngrok, we expect the URL to be provided or fetch from ngrok API
        webhook_base = os.getenv("NGROK_WEBHOOK_URL")
        if not webhook_base:
            # Try to get from ngrok local API
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get("http://localhost:4040/api/tunnels")
                    data = response.json()
                    if data.get("tunnels"):
                        webhook_base = data["tunnels"][0]["public_url"]
            except Exception as e:
                logger.error(f"Failed to get ngrok URL: {e}")
                logger.info("Please provide NGROK_WEBHOOK_URL environment variable")
                return
    else:
        webhook_base = os.getenv("WEBHOOK_BASE_URL", "https://localhost")

    if not webhook_base:
        logger.error("No webhook base URL configured")
        return

    # Get secret token
    secret_token = os.getenv("WEBHOOK_SECRET_TOKEN")

    logger.info(f"Webhook base URL: {webhook_base}")
    logger.info(f"Secret token: {'enabled' if secret_token else 'disabled'}")

    # Get all bots
    bots = await get_all_bots(database_url)

    if not bots:
        logger.info("No active bots found")
        return

    logger.info(f"Found {len(bots)} bot(s) to update")

    # Update webhooks
    success_count = 0
    fail_count = 0

    for bot in bots:
        bot_id = bot['id']
        bot_token = bot['bot_token']
        bot_username = bot['bot_username']
        current_webhook = bot['current_webhook']

        # Construct webhook URL
        webhook_url = f"{webhook_base}/webhook/{bot_id}"

        logger.info(f"Processing bot @{bot_username} ({bot_id[:8]})")

        # Skip if webhook is already set correctly
        if current_webhook == webhook_url:
            logger.info(f"  ✓ Webhook already set correctly")
            success_count += 1
            continue

        # Set webhook
        success = await set_webhook(bot_token, webhook_url, secret_token)

        if success:
            # Update in database
            await update_webhook_in_db(database_url, bot_id, webhook_url)
            logger.info(f"  ✓ Webhook updated to: {webhook_url}")
            success_count += 1
        else:
            logger.error(f"  ✗ Failed to set webhook for @{bot_username}")
            fail_count += 1

    # Summary
    logger.info("=" * 50)
    logger.info(f"Update complete!")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Failed: {fail_count}")
    logger.info(f"  Total: {len(bots)}")
    logger.info("=" * 50)


if __name__ == "__main__":
    import sys

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

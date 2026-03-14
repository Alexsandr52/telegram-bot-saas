#!/usr/bin/env python3
"""
Set Webhook for Telegram Bot
Supports both ngrok (local) and real domain (production)
"""
import asyncio
import httpx
import argparse
from typing import Optional


async def set_webhook(
    bot_token: str,
    webhook_url: str,
    secret_token: Optional[str] = None
) -> bool:
    """
    Set webhook for a Telegram bot

    Args:
        bot_token: Telegram bot token from @BotFather
        webhook_url: Full URL to webhook endpoint
        secret_token: Optional secret token for security

    Returns:
        True if successful, False otherwise
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"

    payload = {
        "url": webhook_url,
        "drop_pending_updates": True  # Drop old updates when setting new webhook
    }

    if secret_token:
        payload["secret_token"] = secret_token

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, json=payload)
            result = response.json()

            if result.get("ok"):
                print(f"✅ Webhook set successfully!")
                print(f"   URL: {webhook_url}")
                if secret_token:
                    print(f"   Secret token: {secret_token}")
                return True
            else:
                print(f"❌ Failed to set webhook")
                print(f"   Error: {result.get('description')}")
                return False

        except Exception as e:
            print(f"❌ Error setting webhook: {e}")
            return False


async def get_webhook_info(bot_token: str) -> dict:
    """
    Get current webhook info

    Args:
        bot_token: Telegram bot token

    Returns:
        Webhook info dict
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(api_url)
            result = response.json()

            if result.get("ok"):
                return result.get("result", {})
            else:
                print(f"❌ Error getting webhook info: {result.get('description')}")
                return {}

        except Exception as e:
            print(f"❌ Error getting webhook info: {e}")
            return {}


async def delete_webhook(bot_token: str) -> bool:
    """
    Delete webhook for a Telegram bot

    Args:
        bot_token: Telegram bot token

    Returns:
        True if successful, False otherwise
    """
    api_url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(api_url)
            result = response.json()

            if result.get("ok"):
                print("✅ Webhook deleted successfully!")
                return True
            else:
                print(f"❌ Failed to delete webhook")
                print(f"   Error: {result.get('description')}")
                return False

        except Exception as e:
            print(f"❌ Error deleting webhook: {e}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Set webhook for Telegram bot"
    )
    parser.add_argument(
        "bot_token",
        help="Telegram bot token from @BotFather"
    )
    parser.add_argument(
        "action",
        choices=["set", "get", "delete"],
        help="Action to perform"
    )
    parser.add_argument(
        "--webhook-url",
        help="Webhook URL (required for 'set' action)"
    )
    parser.add_argument(
        "--secret-token",
        help="Secret token for webhook verification"
    )
    parser.add_argument(
        "--bot-id",
        help="Bot ID (for constructing webhook URL)"
    )

    args = parser.parse_args()

    if args.action == "set":
        webhook_url = args.webhook_url

        if not webhook_url:
            if args.bot_id:
                # Use default webhook format
                webhook_url = f"{args.webhook_url}/webhook/{args.bot_id}"
            else:
                print("❌ --webhook-url is required for 'set' action")
                print("   Or provide --bot-id for default format")
                return 1

        success = asyncio.run(set_webhook(
            bot_token=args.bot_token,
            webhook_url=webhook_url,
            secret_token=args.secret_token
        ))
        return 0 if success else 1

    elif args.action == "get":
        webhook_info = asyncio.run(get_webhook_info(args.bot_token))

        if webhook_info:
            print(f"\n📋 Current Webhook Info:")
            print(f"   URL: {webhook_info.get('url', 'Not set')}")
            print(f"   Pending update count: {webhook_info.get('pending_update_count', 0)}")
            print(f"   Last error date: {webhook_info.get('last_error_date', 'None')}")
            print(f"   Last error message: {webhook_info.get('last_error_message', 'None')}")
            if webhook_info.get('has_custom_certificate'):
                print(f"   Custom certificate: Yes")
        return 0

    elif args.action == "delete":
        success = asyncio.run(delete_webhook(args.bot_token))
        return 0 if success else 1


if __name__ == "__main__":
    exit(main())

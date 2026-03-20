#!/usr/bin/env python3
"""
Simple Webhook Tester
Local webhook endpoint for testing Telegram bot webhooks
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging


app = FastAPI(title="Webhook Tester")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)

logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "webhook-tester",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/{bot_id}",
            "info": "/",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/webhook/{bot_id}")
async def receive_webhook(request: Request, bot_id: str):
    """
    Receive webhook POST request from Telegram

    This is for testing purposes only.
    """
    try:
        # Log the request
        body = await request.json()

        logger.info(f"📨 Webhook received from bot: {bot_id}")
        logger.info(f"   Headers: {dict(request.headers)}")
        logger.info(f"   Body type: {request.headers.get('content-type', 'unknown')}")
        logger.info(f"   Body preview: {str(body)[:500]}")

        # Parse Telegram update structure
        if isinstance(body, dict):
            update_id = body.get('update_id')
            message = body.get('message', {})

            if update_id:
                logger.info(f"   Update ID: {update_id}")

            if message:
                text = message.get('text', 'No text')
                logger.info(f"   Message text: {text}")

                from_user = message.get('from', {})
                if from_user:
                    logger.info(f"   From user: {from_user.get('username', 'N/A')}")

                chat = message.get('chat', {})
                if chat:
                    logger.info(f"   Chat ID: {chat.get('id', 'N/A')}")
                    logger.info(f"   Chat type: {chat.get('type', 'N/A')}")

        # Return success to Telegram
        return JSONResponse(content={"ok": True, "description": "Webhook received"})

    except Exception as e:
        logger.error(f"❌ Error processing webhook: {e}")
        return JSONResponse(
            content={"ok": False, "description": str(e)},
            status_code=500
        )


@app.post("/webhook")
async def receive_webhook_no_id(request: Request):
    """
    Receive webhook without bot_id in URL
    """
    try:
        body = await request.json()
        logger.info(f"📨 Webhook received (no bot_id)")
        logger.info(f"   Body: {str(body)[:500]}")
        return JSONResponse(content={"ok": True, "description": "Received"})

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return JSONResponse(
            content={"ok": False, "description": str(e)},
            status_code=500
        )


@app.get("/webhooks")
async def list_webhooks():
    """List all received webhooks (for testing)"""
    return {
        "message": "Send POST requests to /webhook/{bot_id} to test",
        "available_bots": ["74702bd7", "d485d6dc"],
        "example": "curl -X POST http://localhost:8080/webhook/74702bd7 -d '{\"update_id\": 123}'"
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting webhook tester on port 8080")
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

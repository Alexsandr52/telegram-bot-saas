"""
Middleware for dependency injection
Passes repositories to handlers via context data
"""
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable


class RepositoryMiddleware(BaseMiddleware):
    """
    Middleware to inject repositories into handler data
    Repositories are stored in dispatcher context and passed to each handler
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Add repositories to data before calling handler"""
        # Get repositories from dispatcher (set in lifespan)
        dispatcher = data['dispatcher']

        # Use direct dict access instead of .get()
        data['master_repo'] = dispatcher['master_repo']
        data['bot_repo'] = dispatcher['bot_repo']
        data['subscription_repo'] = dispatcher['subscription_repo']

        return await handler(event, data)

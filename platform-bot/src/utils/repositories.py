"""
Database connection and queries for Platform Bot
Uses asyncpg for async PostgreSQL operations
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager
import asyncpg
from loguru import logger


class Database:
    """
    Async PostgreSQL database client using asyncpg

    Usage:
        db = Database(dsn="postgresql://user:pass@host:port/db")
        await db.connect()

        result = await db.fetchval("SELECT ...")
        await db.execute("INSERT INTO ...")

        await db.close()
    """

    def __init__(self, dsn: str, min_size: int = 10, max_size: int = 20):
        """
        Initialize database connection pool

        Args:
            dsn: PostgreSQL connection string
            min_size: Minimum pool size
            max_size: Maximum pool size
        """
        self.dsn = dsn
        self.min_size = min_size
        self.max_size = max_size
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        """Create connection pool"""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    command_timeout=60,
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise

    async def close(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire connection from pool

        Usage:
            async with db.acquire() as conn:
                result = await conn.fetchval("SELECT ...")
        """
        if self.pool is None:
            await self.connect()

        async with self.pool.acquire() as connection:
            yield connection

    async def execute(self, query: str, *args, timeout: float = None) -> str:
        """
        Execute a query that doesn't return data

        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds

        Returns:
            Execution status string

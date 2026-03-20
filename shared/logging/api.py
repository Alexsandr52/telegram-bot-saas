"""
Logging API - Centralized log management
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from loguru import logger

from models import (
    LogEntry, LogQuery, LogStats, LogLevelCount,
    ServiceLogStats, LogExportRequest, LogCleanupRequest
)
from config import get_logger


router = APIRouter(prefix="/logs", tags=["logging"])


@router.get("/", response_model=List[LogEntry])
async def get_logs(
    level: Optional[str] = Query(None, description="Filter by log level"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(100, ge=1, le=1000, description="Limit results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(None, description="Search in messages")
):
    """
    Get logs with filtering and pagination
    """
    app_logger = get_logger("logging-api")

    try:
        import asyncpg
        import os

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="DATABASE_URL not configured")

        conn = await asyncpg.connect(database_url)

        try:
            # Build query
            conditions = []
            params = []
            param_num = 1

            if level:
                conditions.append(f"level = ${param_num}")
                params.append(level)
                param_num += 1

            if service:
                conditions.append(f"module = ${param_num}")
                params.append(service)
                param_num += 1

            if start_date:
                conditions.append(f"created_at >= ${param_num}")
                params.append(start_date)
                param_num += 1

            if end_date:
                conditions.append(f"created_at <= ${param_num}")
                params.append(end_date)
                param_num += 1

            if search:
                conditions.append(f"message ILIKE ${param_num}")
                params.append(f"%{search}%")
                param_num += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    id,
                    level,
                    module as service,
                    logger,
                    function_name,
                    line_num,
                    message,
                    extra_data,
                    created_at
                FROM system_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ${param_num} OFFSET ${param_num + 1}
            """

            rows = await conn.fetch(query, *params)

            # Convert to LogEntry models
            logs = []
            for row in rows:
                logs.append(LogEntry(
                    id=str(row['id']),
                    level=row['level'],
                    service=row['service'] or "",
                    logger=row['logger'],
                    function_name=row['function_name'],
                    line_num=row['line_num'],
                    message=row['message'],
                    extra_data=row['extra_data'] or {},
                    created_at=row['created_at']
                ))

            app_logger.info(f"Retrieved {len(logs)} log entries")

            return logs

        finally:
            await conn.close()

    except Exception as e:
        app_logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=LogStats)
async def get_log_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """
    Get log statistics
    """
    app_logger = get_logger("logging-api")

    try:
        import asyncpg
        import os

        database_url = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(database_url)

        try:
            conditions = []
            params = []
            param_num = 1

            if start_date:
                conditions.append(f"created_at >= ${param_num}")
                params.append(start_date)
                param_num += 1

            if end_date:
                conditions.append(f"created_at <= ${param_num}")
                params.append(end_date)
                param_num += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    COUNT(*) as total_logs,
                    level,
                    COUNT(*) as level_count
                FROM system_logs
                WHERE {where_clause}
                GROUP BY level
            """

            rows = await conn.fetch(query, *params)

            total_logs = sum(row['level_count'] for row in rows)
            by_level = {row['level']: row['level_count'] for row in rows}

            # Get by service stats
            service_query = f"""
                SELECT
                    module as service,
                    COUNT(*) as total,
                    SUM(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END) as error_count,
                    SUM(CASE WHEN level = 'WARNING' THEN 1 ELSE 0 END) as warning_count
                FROM system_logs
                WHERE {where_clause}
                GROUP BY module
                ORDER BY total DESC
            """

            service_rows = await conn.fetch(service_query, *params)
            by_service = {}

            for row in service_rows:
                by_service[row['service']] = ServiceLogStats(
                    service=row['service'],
                    total_logs=row['total'],
                    error_count=row['error_count'],
                    warning_count=row['warning_count'],
                    last_error=None,
                    last_error_time=None
                )

            app_logger.info(f"Generated statistics for {total_logs} logs")

            return LogStats(
                total_logs=total_logs,
                by_level=by_level,
                by_service=by_service,
                time_range={
                    "start": start_date,
                    "end": end_date
                }
            )

        finally:
            await conn.close()

    except Exception as e:
        app_logger.error(f"Error getting log stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cleanup")
async def cleanup_old_logs(request: LogCleanupRequest):
    """
    Delete old logs from database
    """
    app_logger = get_logger("logging-api")

    try:
        import asyncpg
        import os

        database_url = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(database_url)

        try:
            query = """
                DELETE FROM system_logs
                WHERE created_at < NOW() - INTERVAL '1 day' * $1
            """

            result = await conn.execute(query, request.older_than_days)
            count = int(result.split()[-1])

            app_logger.info(f"Cleaned up {count} old logs")

            return {
                "message": f"Cleaned up {count} old log entries",
                "count": count,
                "older_than_days": request.older_than_days
            }

        finally:
            await conn.close()

    except Exception as e:
        app_logger.error(f"Error cleaning up logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export")
async def export_logs(request: LogExportRequest):
    """
    Export logs as JSON or CSV
    """
    app_logger = get_logger("logging-api")

    try:
        import asyncpg
        import os
        from fastapi.responses import Response

        database_url = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(database_url)

        try:
            conditions = []
            params = []
            param_num = 1

            if request.service:
                conditions.append(f"module = ${param_num}")
                params.append(request.service)
                param_num += 1

            if request.level:
                conditions.append(f"level = ${param_num}")
                params.append(request.level)
                param_num += 1

            if request.start_date:
                conditions.append(f"created_at >= ${param_num}")
                params.append(request.start_date)
                param_num += 1

            if request.end_date:
                conditions.append(f"created_at <= ${param_num}")
                params.append(request.end_date)
                param_num += 1

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"""
                SELECT
                    id,
                    level,
                    module as service,
                    logger,
                    function_name,
                    line_num,
                    message,
                    extra_data,
                    created_at
                FROM system_logs
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT 10000
            """

            rows = await conn.fetch(query, *params)

            logs = []
            for row in rows:
                logs.append({
                    "id": str(row['id']),
                    "level": row['level'],
                    "service": row['service'],
                    "logger": row['logger'],
                    "function_name": row['function_name'],
                    "line_num": row['line_num'],
                    "message": row['message'],
                    "extra_data": row['extra_data'] or {},
                    "created_at": row['created_at'].isoformat()
                })

            if request.format == "csv":
                # CSV export
                import csv
                from io import StringIO

                output = StringIO()
                writer = csv.DictWriter(
                    output,
                    fieldnames=['id', 'level', 'service', 'logger', 'function_name',
                            'line_num', 'message', 'extra_data', 'created_at']
                )
                writer.writerows(logs)

                content = output.getvalue()
                media_type = "text/csv"
                filename = f"logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

            else:
                # JSON export (default)
                import json
                content = json.dumps(logs, indent=2, ensure_ascii=False)
                media_type = "application/json"
                filename = f"logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

            app_logger.info(f"Exported {len(logs)} log entries")

            return Response(
                content=content,
                media_type=media_type,
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )

        finally:
            await conn.close()

    except Exception as e:
        app_logger.error(f"Error exporting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/services")
async def get_services():
    """
    Get list of services that have logs
    """
    app_logger = get_logger("logging-api")

    try:
        import asyncpg
        import os

        database_url = os.getenv("DATABASE_URL")
        conn = await asyncpg.connect(database_url)

        try:
            query = """
                SELECT DISTINCT module as service
                FROM system_logs
                ORDER BY service
            """

            rows = await conn.fetch(query)
            services = [row['service'] for row in rows]

            return {"services": services}

        finally:
            await conn.close()

    except Exception as e:
        app_logger.error(f"Error getting services: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/levels")
async def get_log_levels():
    """
    Get available log levels
    """
    return {
        "levels": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    }

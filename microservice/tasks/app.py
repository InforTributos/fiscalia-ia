import logging

from infrastructure.persistence.connection import get_pool

logger = logging.getLogger(__name__)


async def enqueue(task_name: str, **kwargs):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO task_queue (task_name, payload, status) VALUES ($1, $2::jsonb, 'PENDING')",
            task_name, kwargs,
        )
        logger.info("Task '%s' encolada: %s", task_name, kwargs)


async def process_next():
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "UPDATE task_queue SET status = 'RUNNING', started_at = NOW() "
            "WHERE id = (SELECT id FROM task_queue WHERE status = 'PENDING' "
            "ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED) "
            "RETURNING *"
        )
        return dict(row) if row else None

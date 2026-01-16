"""Background tasks for periodic maintenance"""
import asyncio
import logging
from . import crud, database

logger = logging.getLogger(__name__)


async def cleanup_old_notifications_task(days: int = 7):
    """Periodically clean up notifications older than X days"""
    while True:
        try:
            # Run cleanup every 24 hours
            await asyncio.sleep(86400)  # 24 hours in seconds
            
            logger.info(f"Running periodic cleanup of notifications older than {days} days...")
            db = database.SessionLocal()
            try:
                crud.delete_notifications(db, days)
                logger.info("Notification cleanup completed successfully")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error in notification cleanup task: {e}")

import sys
import json
from loguru import logger
from backend.core.config import settings

def serialize(record):
    subset = {
        "timestamp": record["elapsed"].total_seconds(),
        "level": record["level"].name,
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        # Cloud Run / Google Cloud Logging specific fields
        "severity": record["level"].name,
    }
    if record["extra"]:
        subset.update(record["extra"])
    return json.dumps(subset)

def sink(message):
    serialized = serialize(message.record)
    sys.stdout.write(serialized + "\n")

def setup_logging():
    # Remove default handler
    logger.remove()
    
    # In Cloud Run, we prefer JSON for structured logging
    # For local development, we might want pretty printing
    if settings.FRONTEND_URL.startswith("http://localhost"):
        logger.add(sys.stdout, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    else:
        # Structured logging for Cloud Run
        logger.add(sink)

# Initial setup
setup_logging()

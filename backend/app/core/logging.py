from __future__ import annotations

import json
import logging

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("partselect_agent")


def log_interaction(
    intent: str,
    response_type: str,
    latency_ms: float,
    parse_error: bool = False,
) -> None:
    """Log one structured line per chat interaction."""
    logger.info(
        json.dumps(
            {
                "event": "chat_interaction",
                "intent": intent,
                "response_type": response_type,
                "latency_ms": round(latency_ms, 1),
                "parse_error": parse_error,
            }
        )
    )

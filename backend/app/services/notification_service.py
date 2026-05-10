import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_notification(title: str, message: str) -> bool:
    if not settings.notification_webhook_url:
        return False
    try:
        response = httpx.post(
            settings.notification_webhook_url,
            json={"title": title, "message": message, "text": f"{title}\n\n{message}"},
            timeout=8.0,
        )
        response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("Notification webhook failed: %s", exc)
        return False

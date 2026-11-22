"""Persist in-app notifications and push over WebSocket hub."""

from __future__ import annotations

import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.automation import AppNotification, NotificationSeverity
from app.models.user import User, UserRole
from app.services.automation.realtime import hub

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    *,
    title: str,
    body: str = "",
    category: str = "general",
    severity: str = "info",
    link: str = "",
    user_id: Optional[int] = None,
    notify_admins: bool = True,
    meta: Optional[dict] = None,
) -> list[AppNotification]:
    try:
        sev = NotificationSeverity(severity)
    except ValueError:
        sev = NotificationSeverity.info

    targets: list[Optional[int]] = []
    if user_id:
        targets.append(user_id)
    if notify_admins:
        admins = db.query(User).filter(User.role == UserRole.admin, User.is_active.is_(True)).all()
        for a in admins:
            if a.id not in targets:
                targets.append(a.id)
    if not targets:
        targets = [None]

    created: list[AppNotification] = []
    for uid in targets:
        n = AppNotification(
            user_id=uid,
            title=title[:255],
            body=body[:5000],
            category=category[:64],
            severity=sev,
            link=link[:512],
            meta_json=json.dumps(meta or {}, default=str),
        )
        db.add(n)
        created.append(n)
    db.commit()
    for n in created:
        db.refresh(n)
        payload = {
            "type": "notification",
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "category": n.category,
            "severity": n.severity.value,
            "link": n.link,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        try:
            hub.broadcast_sync(payload)
        except Exception:  # noqa: BLE001
            logger.debug("WS broadcast skipped", exc_info=True)
    return created


def list_notifications(db: Session, *, user_id: int, unread_only: bool = False, limit: int = 50):
    q = db.query(AppNotification).filter(
        (AppNotification.user_id == user_id) | (AppNotification.user_id.is_(None))
    )
    if unread_only:
        q = q.filter(AppNotification.is_read.is_(False))
    return q.order_by(AppNotification.id.desc()).limit(limit).all()


def mark_read(db: Session, *, notification_id: int, user_id: int) -> Optional[AppNotification]:
    n = db.query(AppNotification).filter(AppNotification.id == notification_id).first()
    if not n:
        return None
    if n.user_id is not None and n.user_id != user_id:
        return None
    n.is_read = True
    db.commit()
    db.refresh(n)
    return n


def mark_all_read(db: Session, *, user_id: int) -> int:
    rows = (
        db.query(AppNotification)
        .filter(
            ((AppNotification.user_id == user_id) | (AppNotification.user_id.is_(None))),
            AppNotification.is_read.is_(False),
        )
        .all()
    )
    for n in rows:
        n.is_read = True
    db.commit()
    return len(rows)

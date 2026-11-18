"""Explicit, opt-in retention for validated recovery snapshots.

No retention is applied by default. The caller must supply a policy and invoke
apply_recovery_retention; this avoids silently deleting recovery data.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import time

from emwat_linux.recovery_store import RecoverySnapshotStore


@dataclass(frozen=True)
class RecoveryRetentionPolicy:
    """Optional age and count limits; at least one limit must be configured."""

    max_age_seconds: float | None = None
    max_snapshots: int | None = None

    def __post_init__(self) -> None:
        if self.max_age_seconds is not None and (
            isinstance(self.max_age_seconds, bool)
            or not isinstance(self.max_age_seconds, (int, float))
            or not math.isfinite(self.max_age_seconds)
            or self.max_age_seconds <= 0
        ):
            raise ValueError("max_age_seconds must be a finite positive number")
        if self.max_snapshots is not None and (
            type(self.max_snapshots) is not int or self.max_snapshots < 1
        ):
            raise ValueError("max_snapshots must be a positive integer")
        if self.max_age_seconds is None and self.max_snapshots is None:
            raise ValueError("at least one recovery retention limit is required")


def apply_recovery_retention(
    store: RecoverySnapshotStore,
    policy: RecoveryRetentionPolicy,
    *,
    now: float | None = None,
) -> tuple[str, ...]:
    """Delete expired/excess valid snapshots, returning removed session IDs.

    Invalid or unverifiable snapshots are not enumerated by the store and are
    therefore never deleted by this policy. Newest snapshots are retained.
    The caller controls when this function runs and owns the configured policy.
    """
    current_time = time.time() if now is None else now
    if (
        isinstance(current_time, bool)
        or not isinstance(current_time, (int, float))
        or not math.isfinite(current_time)
    ):
        raise ValueError("now must be a finite number")

    snapshots = list(store.list_snapshots())
    expired: set[str] = set()
    if policy.max_age_seconds is not None:
        cutoff = current_time - policy.max_age_seconds
        expired = {item.session_id for item in snapshots if item.updated_at < cutoff}

    survivors = [item for item in snapshots if item.session_id not in expired]
    if policy.max_snapshots is not None and len(survivors) > policy.max_snapshots:
        survivors.sort(key=lambda item: item.updated_at, reverse=True)
        expired.update(item.session_id for item in survivors[policy.max_snapshots:])

    # Delete oldest first for deterministic behavior; the store validates IDs.
    removed = tuple(
        item.session_id for item in sorted(snapshots, key=lambda item: item.updated_at)
        if item.session_id in expired
    )
    for session_id in removed:
        store.remove_session(session_id)
    return removed


__all__ = ["RecoveryRetentionPolicy", "apply_recovery_retention"]

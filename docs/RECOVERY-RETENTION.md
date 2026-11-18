# Recovery retention policy

The recovery store intentionally has **no automatic deletion policy by default**.
This protects unsaved user work until the desktop product exposes a clear
retention setting and communicates the consequences.

The opt-in `emwat_linux.recovery_retention` module provides two explicit limits:

- `max_age_seconds`: remove validated snapshots older than the configured age.
- `max_snapshots`: retain the newest configured number of valid snapshots.

At least one limit is required; a count limit must be at least one. When both
limits are configured, age expiry is applied first, then the count limit is
applied to the remaining snapshots. Invalid or unverifiable entries are not
enumerated and are not deleted by this policy.

The caller must invoke `apply_recovery_retention(store, policy)` at a deliberate
lifecycle point. The module does not start a timer, delete files during import,
or choose a retention period on behalf of the user. This is policy execution,
not encryption: snapshot bytes remain unencrypted at rest. A production UI
must obtain informed user/admin configuration before enabling it.

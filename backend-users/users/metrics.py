"""
Custom Prometheus metrics for the Users service.
"""
from prometheus_client import Counter, Histogram, Gauge

# Login metrics
LOGIN_ATTEMPTS = Counter(
    'prophotos_login_attempts_total',
    'Total number of login attempts',
    ['status']  # 'success', 'failed', 'blocked'
)

LOGIN_LATENCY = Histogram(
    'prophotos_login_latency_seconds',
    'Time spent processing login requests',
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# User registration metrics
USER_REGISTRATIONS = Counter(
    'prophotos_user_registrations_total',
    'Total number of user registrations',
    ['status']  # 'success', 'failed', 'pending_verification'
)

# Token metrics
TOKEN_VERIFICATIONS = Counter(
    'prophotos_token_verifications_total',
    'Total number of token verification attempts',
    ['status']  # 'valid', 'expired', 'invalid'
)

# Active users (gauge)
ACTIVE_USERS = Gauge(
    'prophotos_active_users',
    'Number of users with valid sessions in the last hour'
)

# Email verification
EMAIL_VERIFICATIONS = Counter(
    'prophotos_email_verifications_total',
    'Total number of email verification attempts',
    ['status']  # 'success', 'failed', 'expired'
)

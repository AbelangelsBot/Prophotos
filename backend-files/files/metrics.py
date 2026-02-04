"""
Custom Prometheus metrics for the Files service.
"""
from prometheus_client import Counter, Histogram, Gauge

# File operations
FILE_UPLOADS = Counter(
    'prophotos_file_uploads_total',
    'Total number of file uploads',
    ['status', 'file_type']  # status: 'success', 'failed'; file_type: 'image', 'video', etc.
)

FILE_DOWNLOADS = Counter(
    'prophotos_file_downloads_total',
    'Total number of file downloads',
    ['status']  # 'success', 'failed', 'unauthorized'
)

FILE_DELETIONS = Counter(
    'prophotos_file_deletions_total',
    'Total number of file deletions',
    ['status']  # 'success', 'failed', 'not_found'
)

# File processing
FILE_COMPRESSION_LATENCY = Histogram(
    'prophotos_file_compression_seconds',
    'Time spent compressing files',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# Storage metrics
STORAGE_BYTES = Gauge(
    'prophotos_storage_bytes_total',
    'Total storage used in bytes'
)

FILES_COUNT = Gauge(
    'prophotos_files_count_total',
    'Total number of files stored'
)

# Batch operations
BATCH_DOWNLOADS = Counter(
    'prophotos_batch_downloads_total',
    'Total number of batch download requests',
    ['status']
)

BATCH_SIZE = Histogram(
    'prophotos_batch_size',
    'Number of files in batch requests',
    buckets=[1, 5, 10, 25, 50, 100]
)

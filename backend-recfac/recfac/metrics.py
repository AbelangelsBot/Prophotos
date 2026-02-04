"""
Custom Prometheus metrics for the Face Recognition service.
"""
from prometheus_client import Counter, Histogram, Gauge

# Face scanning
FACE_SCANS = Counter(
    'prophotos_face_scans_total',
    'Total number of face scan operations',
    ['status', 'scan_type']  # status: 'success', 'failed', 'no_face'; scan_type: 'single', 'multiple', 'folder'
)

FACE_SCAN_LATENCY = Histogram(
    'prophotos_face_scan_seconds',
    'Time spent scanning faces',
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

FACES_DETECTED = Counter(
    'prophotos_faces_detected_total',
    'Total number of faces detected'
)

# Face tagging
FACE_TAGS = Counter(
    'prophotos_face_tags_total',
    'Total number of face tagging operations',
    ['status']  # 'success', 'failed'
)

# Face search
FACE_SEARCHES = Counter(
    'prophotos_face_searches_total',
    'Total number of face search operations',
    ['status']  # 'found', 'not_found', 'failed'
)

FACE_SEARCH_LATENCY = Histogram(
    'prophotos_face_search_seconds',
    'Time spent searching for faces',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# GPU Worker metrics
GPU_WORKER_CALLS = Counter(
    'prophotos_gpu_worker_calls_total',
    'Total number of GPU worker API calls',
    ['endpoint', 'status']  # status: 'success', 'failed', 'timeout'
)

GPU_WORKER_LATENCY = Histogram(
    'prophotos_gpu_worker_latency_seconds',
    'Time spent waiting for GPU worker',
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

# Database stats
PERSONS_COUNT = Gauge(
    'prophotos_persons_count',
    'Total number of persons in database'
)

FACES_COUNT = Gauge(
    'prophotos_faces_count',
    'Total number of faces in database'
)

UNTAGGED_FACES_COUNT = Gauge(
    'prophotos_untagged_faces_count',
    'Number of faces without tags'
)

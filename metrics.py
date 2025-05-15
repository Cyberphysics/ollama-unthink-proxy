from prometheus_client import Counter, Histogram, Gauge, generate_latest
import time

# Define metrics
REQUEST_COUNT = Counter(
    'unthink_proxy_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'unthink_proxy_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'unthink_proxy_active_requests',
    'Number of active requests'
)

THINKING_CONTENT_REMOVED = Counter(
    'unthink_proxy_thinking_content_removed_total',
    'Total number of thinking content blocks removed'
)

OLLAMA_REQUEST_ERRORS = Counter(
    'unthink_proxy_ollama_request_errors_total',
    'Total number of errors when requesting Ollama API',
    ['error_type']
)

class MetricsMiddleware:
    def __init__(self, app):
        self.app = app
        
    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        method = environ.get('REQUEST_METHOD', '')
        
        # Skip metrics for the metrics endpoint itself
        if path == '/metrics':
            return self.app(environ, start_response)
        
        # Track request
        ACTIVE_REQUESTS.inc()
        start_time = time.time()
        
        def custom_start_response(status, headers, exc_info=None):
            # Record metrics after request is processed
            status_code = int(status.split(' ')[0])
            REQUEST_COUNT.labels(method=method, endpoint=path, status=status_code).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(time.time() - start_time)
            ACTIVE_REQUESTS.dec()
            
            return start_response(status, headers, exc_info)
        
        return self.app(environ, custom_start_response)

def get_metrics():
    """Return all metrics in Prometheus format"""
    return generate_latest()
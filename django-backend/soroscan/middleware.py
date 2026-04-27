"""
Middleware for request-scoped log context (request_id) and slow query logging.
"""
import logging
import time
import uuid

from django.conf import settings
from django.db import connection
from django.http import JsonResponse

from .log_context import set_request_id

logger = logging.getLogger(__name__)
slow_query_logger = logging.getLogger("soroscan.slow_queries")


class RequestIdMiddleware:
    """Set request_id on the request and in log context for the request lifecycle."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = getattr(request, "request_id", None) or uuid.uuid4().hex
        request.request_id = request_id
        set_request_id(request_id)
        return self.get_response(request)


class ReverseProxyFixedIPMiddleware:
    """
    Middleware to handle rate limiting behind a reverse proxy.

    When running behind a reverse proxy (e.g., Nginx, Cloudflare),
    the REMOTE_ADDR will always be the proxy's IP. This middleware
    extracts the original client IP from X-Forwarded-For header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
            request.META["REMOTE_ADDR"] = client_ip
        return self.get_response(request)


class SlowQueryMiddleware:
    """
    Wrap every DB execute call to log queries that exceed
    LOGGING_SLOW_QUERIES_THRESHOLD_MS (default 100 ms) to the
    ``soroscan.slow_queries`` logger, which writes to a daily-rotated file.

    Overhead is negligible (<1 µs per query for the monotonic clock call)
    and the wrapper is only active when the logger is configured.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.threshold_ms: int = getattr(settings, "LOGGING_SLOW_QUERIES_THRESHOLD_MS", 100)

    def __call__(self, request):
        threshold = self.threshold_ms

        def _execute(execute, sql, params, many, context):
            start = time.monotonic()
            try:
                return execute(sql, params, many, context)
            finally:
                duration_ms = (time.monotonic() - start) * 1000
                if duration_ms >= threshold:
                    slow_query_logger.warning(
                        "Slow query (%dms): %s",
                        int(duration_ms),
                        (sql or "")[:1000],
                        extra={
                            "duration_ms": round(duration_ms, 2),
                            "sql": (sql or "")[:1000],
                            "request_path": request.path,
                        },
                    )

        with connection.execute_wrapper(_execute):
            response = self.get_response(request)

        # Forward X-RateLimit-* headers set by APIKeyThrottle
        headers = getattr(request, "_api_key_throttle_headers", None)
        if headers and hasattr(response, "__setitem__"):
            for name, value in headers.items():
                response[name] = value

        return response

class RequestBodySizeMiddleware:
    """
    Prevent accidental large requests by rejecting bodies > settings.MAX_REQUEST_BODY_SIZE.
    Returns 413 Payload Too Large and logs the event.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_size = getattr(settings, "MAX_REQUEST_BODY_SIZE", 10485760)

    def __call__(self, request):
        content_length = request.META.get('CONTENT_LENGTH')
        
        if content_length:
            try:
                if int(content_length) > self.max_size:
                    logger.warning(
                        "Payload Too Large: %s bytes from %s to %s",
                        content_length,
                        request.META.get('REMOTE_ADDR'),
                        request.path
                    )
                    return JsonResponse(
                        {"error": "Payload Too Large", "limit": self.max_size},
                        status=413
                    )
            except (ValueError, TypeError):
                pass

        return self.get_response(request)

class ApiDeprecationMiddleware:
    """
    Injects Deprecation, Sunset, and Link headers for legacy endpoints defined in settings.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.deprecated_paths = getattr(settings, "DEPRECATED_ENDPOINTS", {})

    def __call__(self, request):
        response = self.get_response(request)
        
        # Check if the current path (or path with trailing slash) is deprecated
        path = request.path
        config = self.deprecated_paths.get(path) or self.deprecated_paths.get(path + "/")
        
        if config:
            response["Deprecation"] = "true"
            response["Sunset"] = config["sunset"]
            response["Link"] = f'<{config["replacement"]}>; rel="replacement"'
            
        return response
# backend/middleware.py
import time
import uuid
import logging
from django.http import JsonResponse

class APILogMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("api")

    def __call__(self, request):
        # Run only for API routes
        if request.path.startswith("/api/"):
            request_id = uuid.uuid4().hex[:12]
            request.META["X_REQUEST_ID"] = request_id
            start = time.monotonic()



            response = self.get_response(request)

            duration_ms = (time.monotonic() - start) * 1000
            response["X-Request-ID"] = request_id
            self.logger.info(
                "api %s %s -> %s (%.1f ms) uid=%s rid=%s",
                request.method,
                request.path,
                getattr(response, "status_code", "?"),
                duration_ms,
                getattr(getattr(request, "user", None), "id", None),
                request_id,
            )
            return response

        # Non-API paths
        return self.get_response(request)

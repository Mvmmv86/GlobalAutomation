"""Error Sanitization for secure API responses"""

import re
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger(__name__)


class ErrorSanitizer:
    """
    Sanitize error messages before returning to clients.

    Prevents leaking sensitive information like:
    - API keys and secrets
    - Database connection strings
    - Internal file paths
    - Stack traces in production
    - IP addresses and internal infrastructure details
    """

    # Patterns to detect and sanitize
    SENSITIVE_PATTERNS = {
        # API keys and tokens
        'api_key': re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})', re.IGNORECASE),
        'secret': re.compile(r'secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_-]{16,})', re.IGNORECASE),
        'token': re.compile(r'token["\']?\s*[:=]\s*["\']?(Bearer\s+)?([a-zA-Z0-9_.-]{20,})', re.IGNORECASE),
        'password': re.compile(r'password["\']?\s*[:=]\s*["\']?([^\s"\']+)', re.IGNORECASE),

        # Connection strings
        'postgres': re.compile(r'postgresql://[^@]+@[^/]+/[^\s]+', re.IGNORECASE),
        'mysql': re.compile(r'mysql://[^@]+@[^/]+/[^\s]+', re.IGNORECASE),
        'mongodb': re.compile(r'mongodb(\+srv)?://[^@]+@[^\s]+', re.IGNORECASE),
        'redis': re.compile(r'redis://:[^@]+@[^\s]+', re.IGNORECASE),

        # File paths
        'unix_path': re.compile(r'/(?:home|root|var|etc|usr)/[/\w.-]+'),
        'windows_path': re.compile(r'[A-Z]:\\(?:Users|Windows|Program Files)[\\\/\w.-]+'),

        # IP addresses (internal)
        'private_ip': re.compile(r'\b(?:10|127|172\.(?:1[6-9]|2[0-9]|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\b'),

        # Email addresses
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    }

    # Known sensitive exception types
    SENSITIVE_EXCEPTIONS = {
        'psycopg2.OperationalError',
        'pymongo.errors.ConnectionFailure',
        'redis.exceptions.ConnectionError',
        'sqlalchemy.exc.OperationalError',
    }

    # Generic error messages for different scenarios
    GENERIC_MESSAGES = {
        'database': 'Database operation failed. Please try again later.',
        'authentication': 'Authentication failed. Please check your credentials.',
        'authorization': 'Access denied. Insufficient permissions.',
        'validation': 'Invalid request data. Please check your input.',
        'external_service': 'External service temporarily unavailable.',
        'internal': 'An internal error occurred. Please contact support.',
        'rate_limit': 'Rate limit exceeded. Please try again later.',
    }

    def __init__(self, environment: str = "production"):
        """
        Initialize error sanitizer.

        Args:
            environment: Environment (development/production)
                        In development, show more details for debugging
        """
        self.environment = environment.lower()
        self.is_production = self.environment in ["production", "prod"]

    def sanitize_error(
        self,
        error: Exception,
        error_type: str = "internal",
        include_type: bool = False
    ) -> Dict[str, Any]:
        """
        Sanitize error for API response.

        Args:
            error: Original exception
            error_type: Type of error (for generic message selection)
            include_type: Include exception type in response

        Returns:
            Sanitized error dictionary
        """
        error_class = f"{error.__class__.__module__}.{error.__class__.__name__}"
        error_message = str(error)

        # Log original error for debugging
        logger.error(
            "Error occurred",
            error_class=error_class,
            error_message=error_message,
            error_type=error_type
        )

        # In development, return more details
        if not self.is_production:
            return {
                "error": error_type,
                "message": self._sanitize_message(error_message),
                "type": error_class if include_type else None,
                "environment": "development"
            }

        # Production: use generic messages
        generic_message = self.GENERIC_MESSAGES.get(
            error_type,
            self.GENERIC_MESSAGES["internal"]
        )

        response = {
            "error": error_type,
            "message": generic_message
        }

        # Only include exception type for known safe exceptions
        if include_type and not self._is_sensitive_exception(error_class):
            response["type"] = error_class

        return response

    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize a dictionary by removing sensitive values.

        Args:
            data: Dictionary to sanitize

        Returns:
            Sanitized dictionary
        """
        sanitized = {}

        for key, value in data.items():
            # Recursively sanitize nested dicts
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)

            # Sanitize lists
            elif isinstance(value, list):
                sanitized[key] = [
                    self.sanitize_dict(item) if isinstance(item, dict)
                    else self._sanitize_value(key, item)
                    for item in value
                ]

            # Sanitize scalar values
            else:
                sanitized[key] = self._sanitize_value(key, value)

        return sanitized

    def _sanitize_value(self, key: str, value: Any) -> Any:
        """Sanitize a single value based on key name"""
        key_lower = key.lower()

        # Mask sensitive fields by name
        sensitive_keys = {
            'password', 'secret', 'api_key', 'token',
            'private_key', 'access_token', 'refresh_token',
            'apikey', 'api_secret'
        }

        if any(sensitive in key_lower for sensitive in sensitive_keys):
            return "***REDACTED***"

        # Sanitize string values
        if isinstance(value, str):
            return self._sanitize_message(value)

        return value

    def _sanitize_message(self, message: str) -> str:
        """
        Sanitize a message by removing sensitive patterns.

        Args:
            message: Original message

        Returns:
            Sanitized message
        """
        sanitized = message

        # Replace sensitive patterns
        for pattern_name, pattern in self.SENSITIVE_PATTERNS.items():
            if pattern_name in ['api_key', 'secret', 'token', 'password']:
                # Completely redact these
                sanitized = pattern.sub(
                    f'{pattern_name.upper()}=***REDACTED***',
                    sanitized
                )
            elif pattern_name in ['postgres', 'mysql', 'mongodb', 'redis']:
                # Replace with generic connection string
                sanitized = pattern.sub(
                    f'{pattern_name}://***REDACTED***',
                    sanitized
                )
            elif pattern_name in ['unix_path', 'windows_path']:
                # Replace with generic path
                sanitized = pattern.sub(
                    '***PATH_REDACTED***',
                    sanitized
                )
            elif pattern_name == 'private_ip':
                # Replace with placeholder
                sanitized = pattern.sub(
                    '***IP_REDACTED***',
                    sanitized
                )
            elif pattern_name == 'email':
                # Mask email addresses
                sanitized = pattern.sub(
                    '***EMAIL_REDACTED***',
                    sanitized
                )

        return sanitized

    def _is_sensitive_exception(self, exception_class: str) -> bool:
        """Check if exception class is sensitive"""
        return exception_class in self.SENSITIVE_EXCEPTIONS

    def sanitize_stack_trace(self, stack_trace: str) -> Optional[str]:
        """
        Sanitize stack trace.

        In production, returns None.
        In development, returns sanitized trace.

        Args:
            stack_trace: Original stack trace

        Returns:
            Sanitized stack trace or None
        """
        if self.is_production:
            return None

        # In development, sanitize but return
        return self._sanitize_message(stack_trace)

    def create_safe_error_response(
        self,
        error: Exception,
        status_code: int = 500,
        error_type: str = "internal",
        additional_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Create a complete safe error response.

        Args:
            error: Original exception
            status_code: HTTP status code
            error_type: Error type category
            additional_context: Additional safe context to include

        Returns:
            Complete error response dictionary
        """
        response = self.sanitize_error(error, error_type=error_type)
        response["status_code"] = status_code

        # Add safe additional context
        if additional_context:
            safe_context = self.sanitize_dict(additional_context)
            response["context"] = safe_context

        # Add timestamp
        import time
        response["timestamp"] = int(time.time())

        # Add request ID if available (for tracking)
        # This should be set by middleware
        response["request_id"] = additional_context.get("request_id") if additional_context else None

        return response


# Global instance
_error_sanitizer: Optional[ErrorSanitizer] = None


def get_error_sanitizer(environment: str = "production") -> ErrorSanitizer:
    """Get or create global error sanitizer instance"""
    global _error_sanitizer

    if _error_sanitizer is None:
        _error_sanitizer = ErrorSanitizer(environment=environment)

    return _error_sanitizer

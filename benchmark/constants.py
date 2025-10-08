"""
Status and exit code constants following project style guide.

These constants ensure consistent output formatting across all
benchmark tools and match bash script conventions.
"""

# Status indicators (matching bash script conventions)
STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_ERROR = "ERROR"
STATUS_INFO = "INFO"

# Exit codes (Unix standard)
EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_INVALID_USAGE = 2

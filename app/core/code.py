"""
Categorized business response codes.

Code ranges:
  0000        — Success
  1000-1999   — System internal errors (exception captures)
  2000-2999   — Business logic errors (auth, permission, resource, etc.)
  3000-3999   — Internal reserved
  4000-9999   — User business custom (framework does NOT use)

Frontend .env mapping:
  VITE_SERVICE_SUCCESS_CODE=0000
  VITE_SERVICE_LOGOUT_CODES=2100,2101
  VITE_SERVICE_MODAL_LOGOUT_CODES=2102
  VITE_SERVICE_EXPIRED_TOKEN_CODES=2103
"""


class Code:
    """Categorized response codes for the entire application."""

    # ---- 0000 Success ----
    SUCCESS = "0000"

    # ==== 1xxx System Internal Errors ====

    # 10xx — Server errors
    INTERNAL_ERROR = "1000"  # generic / unhandled exception

    # 11xx — Database errors
    INTEGRITY_ERROR = "1100"  # constraint violation (unique, FK, etc.)
    NOT_FOUND = "1101"  # record does not exist

    # 12xx — Validation errors
    REQUEST_VALIDATION = "1200"  # request params / body validation failed
    RESPONSE_VALIDATION = "1201"  # response serialization failed

    # ==== 2xxx Business Logic Errors ====

    # 21xx — Authentication
    INVALID_TOKEN = "2100"  # token missing / decode error / invalid
    INVALID_SESSION = "2101"  # wrong token type / user not found
    ACCOUNT_DISABLED = "2102"  # user account has been disabled
    TOKEN_EXPIRED = "2103"  # access / refresh token expired

    # 22xx — Authorization
    API_DISABLED = "2200"  # API endpoint has been disabled
    PERMISSION_DENIED = "2201"  # RBAC permission denied

    # 23xx — Resource conflicts
    DUPLICATE_RESOURCE = "2300"  # duplicate resource (username, role code, etc.)

    # 24xx — General business failure
    FAIL = "2400"  # generic business logic failure

    # 25xx — Rate limiting / security
    RATE_LIMITED = "2500"  # too many requests
    IP_BANNED = "2501"  # IP temporarily banned
    ACCESS_DENIED = "2502"  # blocked by security guard

    # ==== 3xxx Internal Reserved ====
    # (not used yet, reserved for future framework extensions)

    # ==== 4000-9999 User Business Custom ====
    # (framework does NOT use — available for project-specific business codes)

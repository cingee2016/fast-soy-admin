"""
Response codes aligned with frontend .env configuration.
All business codes are in the 4000-5000 range.

Frontend .env mapping:
  VITE_SERVICE_SUCCESS_CODE=0000
  VITE_SERVICE_LOGOUT_CODES=4001,4002
  VITE_SERVICE_MODAL_LOGOUT_CODES=4003
  VITE_SERVICE_EXPIRED_TOKEN_CODES=4010
"""


class Code:
    """Four-digit response codes (4000-5000) for the entire application."""

    # ---- success ----
    SUCCESS = "0000"

    # ---- generic failure (no special frontend behavior) ----
    FAIL = "4000"

    # ---- logout codes (frontend redirects to login page) ----
    INVALID_TOKEN = "4001"          # token decode error / generic token failure / missing token
    INVALID_SESSION = "4002"        # wrong token type / user not found

    # ---- modal logout codes (frontend shows confirmation modal) ----
    ACCOUNT_DISABLED = "4003"       # user has been disabled (while already logged in)

    # ---- expired token codes (frontend auto-refreshes and retries) ----
    TOKEN_EXPIRED = "4010"          # access/refresh token expired

    # ---- permission codes (frontend shows error message, no logout) ----
    API_DISABLED = "4031"           # API endpoint has been disabled
    PERMISSION_DENIED = "4032"      # RBAC permission denied

    # ---- business codes ----
    DUPLICATE_RESOURCE = "4090"     # duplicate resource (e.g., username, role code)
    VALIDATION_ERROR = "4220"       # request validation error

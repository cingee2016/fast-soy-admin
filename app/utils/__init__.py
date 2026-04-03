"""
Public API for business developers.

This module re-exports commonly used classes and functions so that
business code can import from a single, stable location:

    from app.utils import CRUDBase, CRUDRouter, Success, radar_log

Instead of reaching into internal modules like app.core.* or app.system.*.
"""

# ---- ORM base classes & enums ----
from app.core.base_model import AuditMixin as AuditMixin
from app.core.base_model import BaseModel as BaseModel
from app.core.base_model import IntEnum as IntEnum
from app.core.base_model import StatusType as StatusType
from app.core.base_model import StrEnum as StrEnum

# ---- Schema base classes ----
from app.core.base_schema import CommonIds as CommonIds
from app.core.base_schema import Custom as Custom
from app.core.base_schema import Fail as Fail
from app.core.base_schema import SchemaBase as SchemaBase
from app.core.base_schema import Success as Success
from app.core.base_schema import SuccessExtra as SuccessExtra

# ---- Business errors & codes ----
from app.core.code import Code as Code

# ---- Settings ----
from app.core.config import APP_SETTINGS as APP_SETTINGS

# ---- CRUD ----
from app.core.crud import CRUDBase as CRUDBase

# ---- Context & Auth ----
from app.core.ctx import CTX_USER_ID as CTX_USER_ID
from app.core.ctx import get_current_user as get_current_user
from app.core.ctx import has_button_code as has_button_code
from app.core.ctx import has_role_code as has_role_code
from app.core.ctx import is_super_admin as is_super_admin
from app.core.dependency import DependAuth as DependAuth
from app.core.dependency import DependPermission as DependPermission
from app.core.exceptions import BizError as BizError
from app.core.exceptions import SchemaValidationError as SchemaValidationError

# ---- Logging & monitoring ----
from app.core.log import log as log
from app.core.router import CRUDRouter as CRUDRouter
from app.core.router import SearchFieldConfig as SearchFieldConfig

# ---- Data utilities ----
from app.core.tools import camel_case_convert as camel_case_convert
from app.core.tools import orjson_dumps as orjson_dumps
from app.core.tools import snake_case_convert as snake_case_convert
from app.core.tools import time_to_timestamp as time_to_timestamp
from app.core.tools import timestamp_to_time as timestamp_to_time
from app.core.tools import to_camel_case as to_camel_case
from app.core.tools import to_lower_camel_case as to_lower_camel_case
from app.core.tools import to_snake_case as to_snake_case
from app.core.tools import to_upper_camel_case as to_upper_camel_case
from app.system.radar.developer import radar_log as radar_log

# ---- Security ----
from app.system.security import create_access_token as create_access_token
from app.system.security import get_password_hash as get_password_hash
from app.system.security import verify_password as verify_password

# ---- Init data helpers (for business modules) ----
from app.utils.init_helper import ensure_menu as ensure_menu
from app.utils.init_helper import ensure_role as ensure_role

# ---- User management ----
from app.system.services import CreateUserResult as CreateUserResult
from app.system.services import create_system_user as create_system_user

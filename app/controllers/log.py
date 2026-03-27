from app.core.crud import CRUDBase
from app.models.system import Log
from app.schemas.admin import LogCreate, LogUpdate


class LogController(CRUDBase[Log, LogCreate, LogUpdate]):
    def __init__(self):
        super().__init__(model=Log)


log_controller = LogController()

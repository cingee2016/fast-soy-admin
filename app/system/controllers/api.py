from app.core.crud import CRUDBase
from app.system.models import Api
from app.system.schemas.admin import ApiCreate, ApiUpdate


class ApiController(CRUDBase[Api, ApiCreate, ApiUpdate]):
    def __init__(self):
        super().__init__(model=Api)


api_controller = ApiController()

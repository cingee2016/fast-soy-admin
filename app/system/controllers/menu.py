from loguru import logger
from tortoise.transactions import in_transaction

from app.core.crud import CRUDBase
from app.system.models import Button, Menu
from app.system.radar.developer import radar_log
from app.system.schemas.admin import ButtonBase, MenuCreate, MenuUpdate


class MenuController(CRUDBase[Menu, MenuCreate, MenuUpdate]):
    def __init__(self):
        super().__init__(model=Menu)

    async def get_by_menu_name(self, menu_name: str) -> Menu | None:
        return await self.model.filter(menu_name=menu_name).first()

    async def get_by_route_path(self, route_path: str) -> Menu | None:
        return await self.model.filter(route_path=route_path).first()

    async def get_by_id_list(self, id_list: list[int] | str) -> list[Menu] | None:
        if isinstance(id_list, str):
            id_list = [int(x) for x in id_list.split(",")]
        return await self.model.filter(id__in=id_list)

    @staticmethod
    async def update_buttons_by_code(menu: Menu, buttons: list[ButtonBase] | None = None) -> bool:
        if not buttons:
            return False

        async with in_transaction("conn_system"):
            existing_buttons = [button.button_code for button in await menu.by_menu_buttons]
            menu_buttons = [button.button_code for button in buttons]

            for button_code in set(existing_buttons) - set(menu_buttons):
                logger.error(f"Button Deleted {button_code}")
                radar_log("按钮已删除", level="WARNING", data={"buttonCode": button_code})
                await Button.filter(button_code=button_code).delete()

            await menu.by_menu_buttons.clear()
            for button in buttons:
                button_obj = await Button.filter(button_code=button.button_code).first()
                if button_obj:
                    await Button.filter(id=button_obj.id).update(button_desc=button.button_desc)
                else:
                    button_obj = await Button.create(button_code=button.button_code, button_desc=button.button_desc)
                await menu.by_menu_buttons.add(button_obj)

        return True


menu_controller = MenuController()

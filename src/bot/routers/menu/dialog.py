from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Start, Url
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.bot.routers.dashboard.users.handlers import on_user_search
from src.bot.routers.extra.test import show_dev_popup
from src.bot.states import Dashboard, MainMenu, Subscription
from src.bot.widgets import Banner, I18nFormat, IgnoreUpdate
from src.core.constants import PURCHASE_PREFIX
from src.core.enums import BannerName

from .getters import menu_getter
from .handlers import on_get_trial

menu = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-main-menu"),
    # Row(
    #     Button(
    #         text=I18nFormat(ButtonKey.CONNECT),
    #         id="connect",
    #     ),
    # ),
    Row(
        Button(
            text=I18nFormat("btn-menu-trial"),
            id="trial",
            on_click=on_get_trial,
            when=F["trial_available"],
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-menu-subscription"),
            id=f"{PURCHASE_PREFIX}subscription",
            state=Subscription.MAIN,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu-invite"),
            id="invite",
            on_click=show_dev_popup,
        ),
        Url(
            text=I18nFormat("btn-menu-support"),
            id="support",
            url=Format("{support}"),
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-menu-dashboard"),
            id="dashboard",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
            when=F["middleware_data"]["user"].is_privileged,
        ),
    ),
    MessageInput(func=on_user_search),
    IgnoreUpdate(),
    state=MainMenu.MAIN,
    getter=menu_getter,
)

router = Dialog(menu)

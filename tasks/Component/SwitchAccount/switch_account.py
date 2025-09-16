from adbutils import device

from module.config.config import Config
from module.device.device import Device
from tasks.Component.SwitchAccount.assets import SwitchAccountAssets
from tasks.Component.SwitchAccount.exit_game import ExitGame
from tasks.Component.SwitchAccount.login_account import LoginAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_login
from tasks.base_task import BaseTask
from tasks.Restart.login import LoginHandler

from module.logger import logger


class SwitchAccount(LoginAccount, ExitGame, GameUi, SwitchAccountAssets):

    def __init__(self, config: Config, device: Device, to: AccountInfo, frm: AccountInfo = None):
        """

        @param config:
        @type config:
        @param device:
        @type device:
        @param to: 要登录的账号信息
        @type to:
        @param frm: 上一个账号信息 ,避免关键字from
        @type frm:
        """
        super().__init__(config, device)
        self.to_account_info = to
        self.from_account_info = frm

    def switchAccount(self):
        logger.info("[角色] 开始切换 %s-%s",  self.to_account_info.svr, self.to_account_info.character)
        # 判断所处界面
        curPage = self.ui_get_current_page()

        if curPage != page_login and curPage != page_main:
            self.ui_goto(page_main)
            curPage = self.ui_get_current_page()
        if curPage == page_main:
            self.exitGame()

        # 处于登录界面
        if not self.login(self.to_account_info):
            return False
        logger.info("[角色] %s-%s 登陆成功!", self.to_account_info.svr, self.to_account_info.character)
        # 处理位于登录界面各种奇葩弹窗
        login_handler = LoginHandler(config=self.config, device=self.device)
        login_handler.set_specific_usr(self.to_account_info.svr)
        login_handler.app_handle_login()

        return True


if __name__ == '__main__':
    config = Config('switch')
    device = Device(config)
    account_list = [
        # AccountInfo(account="178****7164", account_alias="178****7164", apple_or_android=True, character="浙沥沥、下雨", svr="全球国际区"),
        # AccountInfo(account="187****4867", account_alias="187****4867", apple_or_android=True, character="紫芪", svr="破晓之樱"),

        AccountInfo(account="187****4867", account_alias="187****4867", apple_or_android=True, character="三千菟", svr="樱之华"),
        AccountInfo(account="150****7970", account_alias="150****7970", apple_or_android=True, character="落地反弹", svr="樱之华"),
        AccountInfo(account="sui94044@163.com", account_alias="sui94044", apple_or_android=True, character="阿岁啊", svr="樱之华"),
        AccountInfo(account="178****7164", account_alias="178****7164", apple_or_android=True, character="浙沥沥、下雨", svr="破晓之樱"),

        AccountInfo(account="150****7970", account_alias="150****7970", apple_or_android=True, character="落地反弹", svr="网易一两情相悦"),
        AccountInfo(account="187****4867", account_alias="187****4867", apple_or_android=True, character="三千卍", svr="旧友新朋"),
        AccountInfo(account="187****4867", account_alias="187****4867", apple_or_android=True, character="唳莅", svr="灵狐愿"),
        AccountInfo(account="187****4867", account_alias="187****4867", apple_or_android=True, character="夜玖幻", svr="游梦迷蝶"),
    ]

    for toAccount in account_list:
        sa = SwitchAccount(config, device, toAccount)
        sa.switchAccount()
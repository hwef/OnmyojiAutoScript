# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
from cached_property import cached_property
from datetime import timedelta, datetime

from module.base.timer import Timer
from module.atom.image_grid import ImageGrid
from module.logger import logger
from module.exception import TaskEnd

from tasks.GameUi.game_ui import GameUi
from tasks.Utils.config_enum import ShikigamiClass
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.KekkaiUtilize.config import UtilizeRule, SelectFriendList
from tasks.KekkaiUtilize.utils import CardClass, target_to_card_class
from tasks.Component.ReplaceShikigami.replace_shikigami import ReplaceShikigami
from tasks.GameUi.page import page_main, page_guild

""" 寮体力 """
class ScriptTask(GameUi, KekkaiUtilizeAssets):

    def run(self):

        # 收寮体力或者资金
        for i in range(3):
            self.ui_get_current_page()
            self.ui_goto(page_guild)
            # 进入寮主页会有一个动画，等一等，让小纸人跑一会儿
            time.sleep(3)

            self.check_guild_ap_or_assets()

            self.ui_get_current_page()
            self.ui_goto(page_main)

        self.set_next_run(task='GuildSushi', success=True, finish=True)
        raise TaskEnd('GuildSushi')

    def check_guild_ap_or_assets(self, ap_enable: bool = True, assets_enable: bool = True) -> bool:
        """
        在寮的主界面 检查是否有收取体力或者是收取寮资金
        如果有就顺带收取
        :return:
        """



        if ap_enable or assets_enable:
            self.screenshot()
            if not self.appear(self.I_GUILD_AP) and not self.appear(self.I_GUILD_ASSETS):
                logger.info('No ap or assets to collect')
                return False
        else:
            return False

        # 如果有就收取
        timer_check = Timer(2)
        timer_check.start()
        while 1:
            self.screenshot()

            # 获得奖励
            if self.ui_reward_appear_click():
                timer_check.reset()

            # 资金收取确认
            if self.appear_then_click(self.I_GUILD_ASSETS_RECEIVE, interval=0.5):
                timer_check.reset()
                continue

            # 收体力
            if self.appear_then_click(self.I_GUILD_AP, interval=1.5):
                timer_check.reset()
                continue
            # 收资金
            if self.appear_then_click(self.I_GUILD_ASSETS, interval=1.5, threshold=0.6):
                timer_check.reset()
                continue

            if timer_check.reached():
                break
        logger.info('Collect ap or assets success')




if __name__ == "__main__":
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
    # t.screenshot()
    # print(t.appear(t.I_BOX_EXP, threshold=0.6))
    # print(t.appear(t.I_BOX_EXP_MAX, threshold=0.6))

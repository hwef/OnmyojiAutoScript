# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from time import sleep

from datetime import datetime, timedelta
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.LBS.assets import LBSAssets

""" LBS """


class ScriptTask(GameUi, GeneralBattle, LBSAssets):

    def run(self):

        self.limit_count = self.config.lbs.lbs_config.limit_count
        limit_time = self.config.lbs.lbs_config.limit_time
        self.limit_time: timedelta = timedelta(
            hours=limit_time.hour,
            minutes=limit_time.minute,
            seconds=limit_time.second
        )

        self.ui_goto_page(page_main)

        self.ui_click(self.I_FLUSH, self.I_1)
        self.ui_click(self.I_1, self.I_2)
        self.ui_click(self.I_2, self.I_3)

        while 1:
            self.screenshot()

            if self.current_count >= self.limit_count:
                logger.info('LBS count limit out')
                break
            if datetime.now() - self.start_time >= self.limit_time:
                logger.info('LBS time limit out')
                break

            self.ui_click(self.I_3, self.I_4)
            self.ui_click(self.I_4, self.I_5)
            sleep(1)
            self.ui_click(self.I_5, self.I_6)
            self.run_general_battle()

        self.set_next_run()
        raise TaskEnd

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 战斗过程 随机点击和滑动 防封
        logger.info("Start battle process")
        self.device.stuck_record_clear()
        self.device.stuck_record_add('BATTLE_STATUS_S')
        while 1:
            self.screenshot()
            if self.appear(self.I_3):
                return True
            if self.appear_then_click(self.I_WIN, interval=1):
                continue
            if self.appear_then_click(self.I_8, interval=1):
                continue
            if self.appear_then_click(self.I_FALSE, threshold=0.8):
                continue
            if self.appear_then_click(self.I_PREPARE_HIGHLIGHT):
                continue
            if self.appear_then_click(self.I_9):
                continue


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('4399')
    # d = Device(c)
    t = ScriptTask(c)
    # t.battle_wait(False)
    t.run()

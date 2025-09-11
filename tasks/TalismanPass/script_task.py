# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_daily
from tasks.TalismanPass.assets import TalismanPassAssets
from tasks.TalismanPass.config import TalismanConfig, LevelReward

from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer

""" 花合战 """
class ScriptTask(GameUi, TalismanPassAssets):

    def run(self):
        self.ui_get_current_page()
        self.ui_goto(page_main)
        self.main_goto_daily()
        con: TalismanConfig = self.config.talisman_pass.talisman

        # 收取全部奖励
        if self.in_task():
            self.get_all()
        # 收取花合战等级奖励
        self.get_flower(con.level_reward)

        self.ui_get_current_page()
        self.ui_goto(page_main)
        self.set_next_run(task='TalismanPass', success=True, finish=True)
        raise TaskEnd('TalismanPass')

    def get_all(self):
        """
        一键收取所有的
        :return:
        """
        self.screenshot()
        if not self.appear(self.I_TP_GET_ALL):
            logger.info('No appear get all button')
        self.ui_get_reward(self.I_TP_GET_ALL)
        logger.info('Get all reward')
        time.sleep(0.5)

    def get_flower(self, level: LevelReward = LevelReward.TWO):
        """
        收取花合战等级奖励
        :return:
        """
        match_level = {
            LevelReward.ONE: self.I_TP_LEVEL_1,
            LevelReward.TWO: self.I_TP_LEVEL_2,
            LevelReward.THREE: self.I_TP_LEVEL_3,
        }
        self.screenshot()
        if not self.appear(self.I_RED_POINT_LEVEL):
            logger.info('No any level reward')
            return
        logger.info('Appear level reward')
        self.ui_click(self.I_RED_POINT_LEVEL, self.I_TP_GET_ALL)
        logger.info('Click level reward')
        check_timer = Timer(2)
        check_timer.start()
        while 1:
            self.screenshot()
            if self.appear_then_click(match_level[level], interval=0.8):
                logger.info(f'Select {level} reward')
                if self.appear_then_click(self.I_OVERFLOW_CONFIRME):
                    pass
                check_timer.reset()
                continue

            if self.ui_reward_appear_click(False):
                logger.info('Get reward')
                check_timer.reset()
                continue
            if check_timer.reached():
                logger.warning('No reward and break')
                break
            if self.appear_then_click(self.I_TP_GET_ALL, interval=2.1):
                logger.info('Get all reward')
                check_timer.reset()
                continue

    def in_task(self) -> bool:
        """
        判断是否在任务的界面
        :return:
        """
        timer = Timer(5)
        timer.start()
        while 1:
            self.screenshot()
            if timer.reached():
                logger.warning('No appear task button')
                return False
            if self.appear(self.I_TP_GOTO) or self.appear(self.I_TP_EXP):
                return True
            if self.appear_then_click(self.I_TP_TASK, interval=1):
                continue

    def main_goto_daily(self):
        """
        无法直接一步到花合战，需要先到主页，然后再到花合战
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_DAILY):
                break
            if self.appear_then_click(self.I_TP_SKIP, interval=1):
                continue
            if self.appear_then_click(self.I_MAIN_GOTO_DAILY, interval=1):
                continue
            if self.ocr_text_threshold(self.O_CLICK_CLOSE_1, interval=2):
                self.click(self.C_CLICK_AREA)
                continue
            if self.ocr_text_threshold(self.O_CLICK_CLOSE_2, interval=2):
                self.click(self.C_CLICK_AREA)
                continue
        logger.info('Page arrive: Daily')
        time.sleep(1)
        return


import os

import cv2
import numpy as np

from numpy import float32, int32, uint8, fromfile
from pathlib import Path

from module.logger import logger
from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr

def load_image(file: str):
    file = Path(file)
    img = cv2.imdecode(fromfile(file, dtype=uint8), -1)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    height, width, channels = img.shape
    if height != 720 or width != 1280:
        logger.error(f'Image size is {height}x{width}, not 720x1280')
        return None
    return img


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('switch')
    d = Device(c)
    t = ScriptTask(c, d)
    # t.screenshot()
    d.image = load_image(r"D:\共享文件夹\Screenshots\花合战\1 (1).png")
    t.main_goto_daily()
    t.run()


# This Python file uses the following encoding: utf-8
# @author ghg11
# github https://github.com/ghg11
from time import sleep
from enum import Enum
from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer
from datetime import timedelta, datetime

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_summon
from tasks.GameUi.page import page_main
from tasks.MemoryScrolls.assets import MemoryScrollsAssets
from tasks.MemoryScrolls.config import ScrollNumber


class ScriptTask(GameUi, MemoryScrollsAssets):

    def run(self):        
        self.ui_get_current_page()
        self.ui_goto(page_summon)

        con = self.config.memory_scrolls.memory_scrolls_config
        # 进入绘卷主界面
        self.goto_memoryscrolls_main(con)

        self.ui_get_current_page()
        self.ui_goto(page_main)

        # 设置下一次运行时间
        self.set_next_run(task='MemoryScrolls', success=True)
        raise TaskEnd
    
    def goto_memoryscrolls_main(self, con):
        # 循环寻找&点击绘卷入口
        self.ui_click(self.I_MS_ENTER, self.I_MS_MAIN)
        # 进入指定分卷
        self.goto_scroll(con)
        # 返回召唤界面，目前只发现此种返回按键
        self.ui_click_until_disappear(self.I_MS_BACK, interval=1)
        logger.info('已返回召唤界面')

    def goto_scroll(self, con):
        """
        进入指定分卷
        :param scroll_number: 分卷编号
        """
        while 1:
            self.screenshot()
            # 暂时用手动截取叉号，后续替换为通用图片
            if self.appear(self.I_MS_CLOSE):
                logger.info('进入绘卷捐献页面')
                break
            match con.scroll_number:
                case ScrollNumber.ONE:
                    self.click(self.C_MS_SCROLL_1, interval=1)
                case ScrollNumber.TWO:
                    self.click(self.C_MS_SCROLL_2, interval=1)
                case ScrollNumber.THREE:
                    self.click(self.C_MS_SCROLL_3, interval=1)
                case ScrollNumber.FOUR:
                    self.click(self.C_MS_SCROLL_4, interval=1)
                case ScrollNumber.FIVE:
                    self.click(self.C_MS_SCROLL_5, interval=1)
                case ScrollNumber.SIX:
                    self.click(self.C_MS_SCROLL_6, interval=1)
                case _:
                    logger.error(f'未知的绘卷编号：{con.scroll_number}')

        # 判断是否需要捐献碎片
        if self.appear(self.I_MS_CONTRIBUTE) or not self.appear(self.I_MS_COMPLETE):
            logger.info(f'正在为{con.scroll_number}捐献碎片')
            self.contribute_memoryscrolls()
        else:
            message = f'{con.scroll_number}进度100%'
            logger.info(message)
            if con.close_task:
                # 关闭探索任务
                logger.info('关闭探索任务')
                self.config.exploration.scheduler.enable = False
                logger.info('关闭绘卷任务')
                self.config.memory_scrolls.scheduler.enable = False
                self.config.save()
                self.push_notify(content=message)

        # 返回绘卷主界面
        self.ui_click_until_disappear(self.I_MS_CLOSE, interval=1)
        logger.info('已退出绘卷捐献界面')

    def contribute_memoryscrolls(self):
        """
        捐献碎片
        :return: None
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_MS_ZERO_S) and self.appear(self.I_MS_ZERO_M) and self.appear(self.I_MS_ZERO_L):
                logger.info('全部绘卷已捐献')
                return
            self.swipe(self.S_MS_SWIPE_S, interval=1)
            self.swipe(self.S_MS_SWIPE_M, interval=1)
            self.swipe(self.S_MS_SWIPE_L, interval=1)
            if self.appear_then_click(self.I_MS_CONTRIBUTE, interval=3):
                logger.info('已捐献记忆绘卷')
                # 等待捐献动画结束
                while 1:
                    self.screenshot()
                    if self.wait_until_appear(self.I_MS_CONTRIBUTED, wait_time=5):
                        self.click(self.C_MS_CONTRIBUTED, interval=1)
                    else:
                        break
    

if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('MI')
    d = Device(c)
    t = ScriptTask(c, d)
    t.screenshot()

    t.run()






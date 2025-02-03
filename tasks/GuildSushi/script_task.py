# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from module.base.timer import Timer
from module.logger import logger
from module.exception import TaskEnd

from tasks.GameUi.game_ui import GameUi
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.Restart.assets import RestartAssets

from tasks.GameUi.page import page_main, page_guild
from datetime import datetime, time
from tasks.base_task import BaseTask, Time

""" 寮体力 """


class ScriptTask(GameUi, KekkaiUtilizeAssets, RestartAssets):

    def run(self):

        for i in range(3):
            # 收寮体力或者资金
            self.check_guild_ap_or_assets()
            # 定时领体力（每天 12-14、20-22 时内各有 20 体力）
            self.harvest()

        # 获取当前时间
        now = datetime.now()
        # 判断当前时间是否在上午10点到中午12点之间
        if time(10, 00) <= now.time() < time(12, 00):
            # 如果当前时间在上午10点到中午12点之间，则设置下一次运行时间为中午12:30
            self.custom_next_run(task='GuildSushi', custom_time=Time(hour=12, minute=30, second=0), time_delta=0)
        # 判断当前时间是否在下午18点到晚上20点之间
        elif time(18, 00) <= now.time() < time(20, 0):
            # 如果当前时间在下午18点到晚上20点之间，则设置下一次运行时间为晚上21点
            self.custom_next_run(task='GuildSushi', custom_time=Time(hour=21, minute=0, second=0), time_delta=0)
        else:
            # 如果当前时间不在上述两个时间段内，则直接设置任务成功完成
            self.set_next_run(task='GuildSushi', success=True, finish=True)

        raise TaskEnd('GuildSushi')

    def check_guild_ap_or_assets(self, ap_enable: bool = True, assets_enable: bool = True) -> bool:
        """
        在寮的主界面 检查是否有收取体力或者是收取寮资金
        如果有就顺带收取
        :return:
        """
        self.ui_get_current_page()
        self.ui_goto(page_guild)

        # 如果有就收取
        timer_check = Timer(3)
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

    def harvest(self):
        """
        获得奖励
        :return: 如果没有发现任何奖励后退出
        """
        self.ui_get_current_page()
        self.ui_goto(page_main)

        current_time = datetime.now().time()
        if not (time(12, 00) <= current_time < time(14, 00) or
                time(20, 00) <= current_time < time(22, 00)):
            return

        timer_harvest = Timer(3)  # 如果连续3秒没有发现任何奖励，退出
        timer_harvest.start()
        while 1:
            self.screenshot()

            # 点击'获得奖励'
            if self.ui_reward_appear_click():
                timer_harvest.reset()
                continue
            # 获得奖励
            if self.appear_then_click(self.I_UI_AWARD, interval=0.2):
                timer_harvest.reset()
                continue
            # 偶尔会打开到聊天频道
            if self.appear_then_click(self.I_HARVEST_CHAT_CLOSE, interval=1):
                timer_harvest.reset()
                continue

            # 体力
            if self.appear_then_click(self.I_HARVEST_AP, interval=1, threshold=0.7):
                timer_harvest.reset()
                continue

            # 红色的关闭
            if self.appear_then_click(self.I_UI_BACK_RED, interval=2.3):
                timer_harvest.reset()
                continue
            # 红色的关闭
            if self.appear(self.I_LOGIN_RED_CLOSE_1):
                self.click(self.I_LOGIN_RED_CLOSE_1, interval=2)
                timer_harvest.reset()
                continue

            # 三秒内没有发现任何奖励，退出
            if timer_harvest.reached():
                break


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

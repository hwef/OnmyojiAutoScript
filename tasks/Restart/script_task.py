# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime

from tasks.Restart.config_scheduler import Scheduler
from tasks.Restart.login import LoginHandler
from tasks.Restart.assets import RestartAssets
from tasks.base_task import BaseTask, Time
from datetime import datetime, time

from module.logger import logger
from module.exception import TaskEnd, RequestHumanTakeover


class ScriptTask(LoginHandler):

    def run(self) -> None:
        """
        主要就是登录的模块
        :return:
        """
        # 每日第一次启动游戏，运行日志备份
        if self.config.back_up.scheduler.enable and self.config.back_up.back_up_config.backup_date != str(datetime.now().date()) :
            self.set_next_run(task='BackUp', target=datetime.now())
        # 每日第一次启动游戏，运行集体任务
        if self.config.collective_missions.missions_config.enable and self.config.collective_missions.missions_config.task_date != str(datetime.now().date()):
            self.set_next_run(task='CollectiveMissions', target=datetime.now())
        if not self.delay_pending_tasks():
            self.app_restart()
        raise TaskEnd('ScriptTask end')

    def app_stop(self):
        logger.hr('App stop')
        self.device.app_stop()

    def app_start(self):
        logger.hr('App start')
        self.device.app_start()
        self.app_handle_login()
        # self.ensure_no_unfinished_campaign()

    def app_restart(self):
        logger.hr('App restart')
        self.device.app_stop()
        self.device.app_start()
        self.app_handle_login()

        # 如果启用了定时领体力（每天 12-14、20-22 时内各有 20 体力）
        if self.config.restart.harvest_config.enable_ap:
            now = datetime.now()
            # 检查是否在12:00-14:00或20:00-22:00时间段内
            in_ap_time_1 = time(12, 0) <= now.time() < time(14, 0)
            in_ap_time_2 = time(20, 0) <= now.time() < time(22, 0)

            # 如果当前在领体力时间段内，设置下一次重启时间为下一个时间段
            if in_ap_time_1 or in_ap_time_2:
                # 如果在12:00-14:00之间，设置为当日21:50
                if in_ap_time_1:
                    self.custom_next_run(task='Restart', custom_time=Time(hour=21, minute=50, second=0), time_delta=0)
                # 如果在20:00-22:00之间，设置为次日13:50
                else:
                    self.custom_next_run(task='Restart', custom_time=Time(hour=13, minute=50, second=0), time_delta=1)
            else:
                # 如果不在领体力时间段内，根据当前时间设置最近的重启时间
                # 如果时间在00:00-13:50之间则设定时间为当日 13:50 时
                if now.time() < time(13, 50):
                    self.custom_next_run(task='Restart', custom_time=Time(hour=13, minute=50, second=0), time_delta=0)
                # 如果时间在13:50-21:50之间则设定时间为当日 21:50 时
                elif time(13, 50) <= now.time() < time(21, 50):
                    self.custom_next_run(task='Restart', custom_time=Time(hour=21, minute=50, second=0), time_delta=0)
                # 如果时间在21:50-23:59之间则设定时间为次日 13:50 时
                else:
                    self.custom_next_run(task='Restart', custom_time=Time(hour=13, minute=50, second=0), time_delta=1)
        else:
            # 未启用体力领取时，设置默认的重启间隔（30分钟后）
            logger.info('未启用体力领取，设置默认重启间隔30分钟')
            self.set_next_run(task='Restart', success=True, finish=True, server=True)

    def delay_pending_tasks(self) -> bool:
        """
        周三更新游戏的时候延迟
        @return:
        """
        datetime_now = datetime.now()
        if not (datetime_now.weekday() == 2 and 7 <= datetime_now.hour <= 8):
            return False
        logger.warning("周三游戏更新,7:00-8:59的任务延迟到9:00")
        # running 中的必然是 Restart
        for task in self.config.pending_task:
            print(task.command)
            self.set_next_run(task=task.command, target=datetime_now.replace(hour=9, minute=0, second=0, microsecond=0))
        return True


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    config = Config('switch')
    device = Device(config)
    s = ScriptTask(config, device)
    # s.run()
    s.app_start()
    # task.config.update_scheduler()
    # task.delay_pending_tasks()
    # task.app_restart()
    # task.screenshot()
    # print(task.appear_then_click(task.I_LOGIN_SCROOLL_CLOSE, threshold=0.9))









# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import json
from datetime import datetime
from datetime import timedelta, time
from module.exception import SwitchAccountError
from module.logger import logger
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from tasks.GameUi.game_ui import GameUi
from module.exception import TaskEnd
from tasks.SwitchAccountOnce.base_channel_task import BaseChannelTask
from tasks.SwitchAccountConfig.config import SwitchAccountConfig

""" 账号切换 """


class ScriptTask(GameUi):
    def __init__(self, config, device):
        super().__init__(config, device)
        self.BaseChannelTask = BaseChannelTask(self.config, self.device)

    account_info = ""
    task_finsh = False

    def run(self):
        con = self.config.switch_account_loop
        accounts_file = con.loop_config.accounts_file

        task_type = "loop_task_time"

        # 加载所有账号数据
        with open(f'config/SwitchAccount/{accounts_file}', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        for index, current_account_data in enumerate(all_accounts_data):
            # 初始化任务信息
            self.account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"
            # 开始账号切换 设置循环任务
            self.switch_account(con, current_account_data, index, task_type)

        # 所有角色任务均已完成
        self.BaseChannelTask.set_wait_task_time()
        self.set_next_run(task=self.config.task.command, target=self.get_next_execution_times())
        self.BaseChannelTask.update_all_account_data(accounts_file, all_accounts_data,  task_type, "未执行")
        raise TaskEnd

    def switch_account(self, con, current_account_data, index, task_type):

        # 任务完成情况检查
        now = datetime.now()
        taskCompleteTime = current_account_data.get(f"{task_type}")
        if taskCompleteTime == str(now.date()):
            logger.info(f"[角色] {self.account_info}, 已完成[循环任务], 跳过")
            return

        account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"

        logger.info(f"[角色] {account_info}, 开始切换...")

        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            password=current_account_data.get("password", False),
            account_alias=current_account_data.get("accountAlias"),
            apple_or_android=current_account_data.get("appleOrAndroid", True),
            character=current_account_data.get("character"),
            svr=current_account_data.get("svr"),
            enable_wy=current_account_data.get("enable_wy", True),
        )

        sa = SwitchAccount(self.config, self.device, toAccount)
        login = sa.switchAccount()
        if login:
            self.config.switch_account_config.config.account_name = account_info
            self.config.save()
            logger.info(f"[角色] {account_info}, 切换完成")
            loop_task = current_account_data.get("loop_task").split(",")
            loop_task.append(f"{self.config.task.command}")
            for task in loop_task:
                self.set_next_run(task=task, target=datetime.now())
            self.BaseChannelTask.update_account_data(con.loop_config.accounts_file, current_account_data, index, task_type, None)
            raise TaskEnd
        else:
            raise SwitchAccountError(f"[角色] {account_info}, 切换失败")

    def get_next_execution_times(self, start_hour=7, end_hour=23, interval_hours=2, execution_minute=30):
        """
        获取下次执行时间，支持动态配置
        在指定时间范围内每隔interval_hours小时执行一次，执行时间为每个小时的execution_minute分钟

        Args:
            start_hour: 开始执行的小时数（默认11点）
            end_hour: 结束执行的小时数（默认23点）
            interval_hours: 执行间隔小时数（默认2小时）
            execution_minute: 执行分钟数（默认30分）

        Returns:
            datetime: 下次执行时间
        """
        now = datetime.now()
        # now = now.replace(hour=23, minute=31, second=0, microsecond=0)

        # 从start_hour开始，每隔interval_hours小时生成执行时间点
        execution_times = []
        hour = start_hour
        while hour <= end_hour:
            execution_times.append(hour)
            hour += interval_hours

        # 查找下一个执行时间
        next_hour = None
        for hour in execution_times:
            candidate_time = now.replace(hour=hour, minute=execution_minute, second=0, microsecond=0)
            if candidate_time > now:
                next_hour = hour
                break

        # 如果今天没有可执行的时间了，则设置为第二天的第一次执行时间
        if next_hour is None:
            next_time = now.replace(hour=start_hour, minute=execution_minute, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_time = now.replace(hour=next_hour, minute=execution_minute, second=0, microsecond=0)

        return next_time


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    config = Config('wy')
    device = Device(config)
    t = ScriptTask(config, device)
    a = t.get_next_execution_times()
    print(a)
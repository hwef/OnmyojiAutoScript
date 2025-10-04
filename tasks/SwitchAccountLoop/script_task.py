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

    def get_next_execution_times(self):
        now = datetime.now()
        # 从当前时间开始计算
        next_hour = now.hour + 1 if now.minute >= 30 else now.hour
        # 找到下一个符合条件的小时（奇数小时）
        next_hour = next_hour if next_hour % 2 == 1 else next_hour + 1

        if next_hour > 23:
            # 如果超过23点，则转到第二天
            next_time = now.replace(hour=15, minute=30, second=0, microsecond=0) + timedelta(days=1)
        else:
            next_time = now.replace(hour=next_hour, minute=30, second=0, microsecond=0)
            if next_time <= now:
                next_time += timedelta(hours=2)

        return next_time


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    config = Config('wy_loop')
    device = Device(config)
    t = ScriptTask(config, device)
    t.run()
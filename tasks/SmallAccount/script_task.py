# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum

import json
from module.logger import logger
from datetime import datetime, timedelta
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from module.exception import TaskEnd
from tasks.GameUi.game_ui import GameUi

""" 小号切换 """


class TaskType(str, Enum):
    dailyTask = 'dailyTaskCompleteTime'
    limitTask = 'limitTaskCompleteTime'
    weekTask  = 'weekTaskCompleteTime'


class ScriptTask(GameUi):
    # 跳过的任务
    skip_task = ['Restart', 'BackUp']
    # 周任务只在周一 运行
    week_task = ['RichMan', 'WeeklyTrifles']
    # 限时任务 晚上7点后运行
    limit_task = ['Hunt', 'DemonEncounter', 'CollectiveMissions']
    task_type = ''
    
    def run(self):
        con = self.config.small_account

        logger.info('开始读取配置文件')
        with open('config/SmallAccount/accounts.json', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        # 日常任务
        logger.hr('设置日常任务', 1)
        self.task_type = "日常任务"
        self.run_task(con, all_accounts_data, TaskType.dailyTask)

        # 获取当前时间
        now = datetime.now()
        # 判断当前时间是否超过19点
        limit_task_run_time = 19
        if now.hour > limit_task_run_time or (now.hour == limit_task_run_time and now.minute >= 0):
            # 限时任务
            logger.hr('设置限时任务', 1)
            self.task_type = "限时任务"
            self.run_task(con, all_accounts_data, TaskType.limitTask)

            # 周任务
            logger.hr('设置周任务', 1)
            self.task_type = "周任务"
            self.run_task(con, all_accounts_data, TaskType.weekTask)

            # 所有角色任务已完成
            self.all_account_complete_task(con)
        else:
            con.small_account_name.account_name = "未知角色"
            self.config.save()
            logger.info(f'等待 {limit_task_run_time}:00, 运行限时任务')
            self.set_next_run(task='SmallAccount', target=datetime.now().replace(hour=limit_task_run_time, minute=0, second=0, microsecond=0))

        raise TaskEnd('SmallAccount')

    def run_task(self, con, all_accounts_data, task_type):
        for index, current_account_data in enumerate(all_accounts_data):
            taskCompleteTime = current_account_data.get(f"{task_type}")

            # 判断是否是今天的日期
            if taskCompleteTime == str(datetime.now().date()):
                logger.info(f"角色 [{current_account_data.get('character')}], [{self.task_type}]已完成, 跳过")
                continue
            else:
                logger.info(f"角色 [{current_account_data.get('character')}] 上次任务完成时间: {taskCompleteTime}")

            # 切换角色
            self.switch_account(con, current_account_data)
            # 设置角色任务
            self.set_task(current_account_data, all_accounts_data, task_type, taskCompleteTime)

            self.set_next_run(task='SmallAccount', target=datetime.now() + timedelta(minutes=1))
            raise TaskEnd('SmallAccount')

    def switch_account(self, con, current_account_data):
        logger.info(f"角色 [{current_account_data.get('character')}] 开始切换...")
        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            account_alias=current_account_data.get("accountAlias"),
            apple_or_android=current_account_data.get("appleOrAndroid"),
            character=current_account_data.get("character"),
            svr=current_account_data.get("svr"),
        )
        sa = SwitchAccount(self.config, self.device, toAccount)
        sa.switchAccount()
        con.small_account_name.account_name = current_account_data.get("character")
        self.config.save()
        logger.info(f"角色 [{current_account_data.get('character')}] 切换完成")
    
    def set_task(self, current_account_data, all_accounts_data, task_type, taskCompleteTime):
        logger.info(f"角色 [{current_account_data.get('character')}] 开始调起任务")
        target_time = datetime(2000, 1, 1)
        match task_type:
            # 日常任务
            case TaskType.dailyTask:
                for task in self.config.waiting_task:
                    if task.command in set(self.skip_task) | set(self.week_task) | set(self.limit_task):
                        continue
                    self.set_next_run(task=task.command, target=target_time)
            # 限时任务
            case TaskType.limitTask:
                for task in self.limit_task:
                    self.set_next_run(task=task, target=target_time)
                # 单独设置蹭卡任务
                self.set_next_run(task="KekkaiUtilize", target=target_time)
            case TaskType.weekTask:
                now = datetime.now()
                start_of_week = now - timedelta(days=now.weekday())  # 计算当前周的起始日期（周一）
                end_of_week = start_of_week + timedelta(days=6)      # 计算当前周的结束日期（周日）
                taskCompleteTime_dt = datetime.strptime(taskCompleteTime, "%Y-%m-%d")  # 将 taskCompleteTime 转换为 datetime 对象
                # 判断目标日期是否在当前周范围内
                if start_of_week <= taskCompleteTime_dt <= end_of_week:
                    for task in self.week_task:
                        self.set_next_run(task=task, target=target_time)
                else:
                    logger.info(f"角色 [{current_account_data.get('character')}] 本周任务完成时间: {taskCompleteTime}")
                    return

        # 更新日常任务完成时间，保存更新后的配置文件
        datetoday = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"角色 [{current_account_data.get('character')}] 更新 {task_type}: {datetoday}")
        current_account_data[f"{task_type}"] = datetoday
        with open('config/SmallAccount/accounts.json', 'w', encoding='utf-8') as file:
            json.dump(all_accounts_data, file, ensure_ascii=False, indent=4)

    def all_account_complete_task(self, con):
        logger.info('所有角色任务已完成')
        con.small_account_name.account_name = "未知角色"
        self.config.save()
        target_time = datetime(2099, 1, 1)
        for task in self.config.waiting_task:
            self.set_next_run(task=task.command, target=target_time)
        self.set_next_run(task='SmallAccount', success=True, finish=True)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('switch')
    d = Device(c)
    t = ScriptTask(c, d)
    t.run()

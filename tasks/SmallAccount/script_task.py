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


class ScriptTask(GameUi):
    skip_task = ['Restart', 'BackUp']
    week_task = ['RichMan', 'WeeklyTrifles']
    limit_task = ['DemonEncounter']
    
    def run(self):
        con = self.config.small_account

        logger.info('开始读取配置文件')
        with open('config/SmallAccount/accounts.json', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        # 日常任务
        self.run_task(con, all_accounts_data, TaskType.dailyTask)

        self.set_next_run(task='SmallAccount', target=datetime.now().remove(hour=19, minute=0, second=0, microsecond=0))
        # 获取当前时间
        now = datetime.now()
        # 判断当前时间是否超过19点
        if now.hour > 19 or (now.hour == 19 and now.minute >= 0):
            # 限时任务
            self.run_task(con, all_accounts_data, TaskType.limitTask)
            # 所有角色任务已完成
            self.all_account_complete_task(con)

        raise TaskEnd('SmallAccount')

    def run_task(self, con, all_accounts_data, task_complete_time):
        for index, current_account_data in enumerate(all_accounts_data):
            taskCompleteTime = current_account_data.get(f"{task_complete_time}")

            # 判断是否是今天的日期
            if taskCompleteTime == str(datetime.now().date()):
                logger.info(f"角色 [{current_account_data.get('character')}], 今天{taskCompleteTime}任务已完成, 跳过")
                continue
            else:
                logger.info(f"角色 {current_account_data.get('character')} 上次任务完成时间: {taskCompleteTime}")

            # 切换角色
            self.switch_account(con, current_account_data)
            # 设置角色今天任务
            self.set_today_task(current_account_data, all_accounts_data, task_complete_time)

            self.set_next_run(task='SmallAccount', target=datetime.now() + timedelta(minutes=1))
            raise TaskEnd('SmallAccount')

    def switch_account(self, con, current_account_data):
        logger.info(f"角色 {current_account_data.get('character')} 开始切换...")
        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            account_alias=current_account_data.get("accountAlias"),
            apple_or_android=current_account_data.get("appleOrAndroid"),
            character=current_account_data.get("character"),
            svr=current_account_data.get("svr"),
        )
        sa = SwitchAccount(self.config, self.device, toAccount)
        sa.switchAccount()
        con.small_account_name.name = current_account_data.get("character")
        self.config.save()
        logger.info(f"角色 {current_account_data.get('character')} 切换完成")
    
    def set_today_task(self, current_account_data, all_accounts_data, task_complete_time):
        logger.info(f"角色 {current_account_data.get('character')} 开始调起任务")
        target_time = datetime(2000, 1, 1)
        # 判断是否是限时任务
        if task_complete_time == TaskType.limitTask:
            for task in self.limit_task:
                self.set_next_run(task=task, target=target_time)
        elif task_complete_time == TaskType.dailyTask:
            # 判断今天是否是周一
            today = datetime.today()
            current_weekday = today.weekday()  # 周一为0，周日为6
            for task in self.config.waiting_task:
                if task.command in self.skip_task:
                    continue
                # 今天不是周一,跳过一周一次的周任务
                if current_weekday != 0:
                    if task.command in self.week_task:
                        continue
                if task.command in self.limit_task:
                    continue
                self.set_next_run(task=task.command, target=target_time)
        else:
            logger.error("传入任务类型异常")
            raise TaskEnd('SmallAccount')

        # 更新日常任务完成时间，保存更新后的配置文件
        datetoday = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"角色 {current_account_data.get('character')} 更新{task_complete_time}任务,完成时间: {datetoday}")
        current_account_data[f"{task_complete_time}"] = datetoday
        with open('config/SmallAccount/accounts.json', 'w', encoding='utf-8') as file:
            json.dump(all_accounts_data, file, ensure_ascii=False, indent=4)

    def all_account_complete_task(self, con):
        logger.info('所有角色任务已完成')
        con.small_account_name.name = "未知角色"
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

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
    weekTask = 'weekTaskCompleteTime'
    assist50 = 'Assist50Time'


class ScriptTask(GameUi):
    # 跳过的任务
    skip_task = ['Restart', 'BackUp']
    # 周任务只在周一 运行
    week_task = ['RichMan', 'WeeklyTrifles']
    # 限时任务 晚上7点后运行
    limit_task = ['Hunt', 'DemonEncounter', 'CollectiveMissions']
    # 协站50运行的任务
    assist50_run_task = ['EvoZone']
    # 总是运行的任务
    always_run_task = ['KekkaiUtilize', 'TalismanPass']
    task_type = ''
    account_info = ''
    
    def run(self):
        con = self.config.small_account

        logger.info('开始读取配置文件')
        # 加载所有账号数据
        with open('config/SmallAccount/accounts.json', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        # ===== 执行日常任务 =====
        self.task_type = "日常任务"
        self.run_task(con, all_accounts_data, TaskType.dailyTask)

        # ===== 执行协战任务 =====
        self.task_type = "协战任务"
        self.run_task(con, all_accounts_data, TaskType.assist50)

        # ===== 执行周任务 =====
        self.task_type = "周任务"
        self.run_task(con, all_accounts_data, TaskType.weekTask)

        # ===== 执行限时任务 =====
        self.task_type = "限时任务"
        self.run_task(con, all_accounts_data, TaskType.limitTask)

        # 所有角色任务均已完成
        self.all_account_complete_task(con)

    def run_task(self, con, all_accounts_data, task_type):
        logger.hr(f'{self.task_type}', 1)
        for index, current_account_data in enumerate(all_accounts_data):
            taskCompleteTime = current_account_data.get(f"{task_type}")
            now = datetime.now()

            self.account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"

            # 判断是否只做协站50任务
            if bool(current_account_data.get('isOnlyAssist50')):
                if task_type == TaskType.assist50:
                    if taskCompleteTime == str(now.date()):
                        logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                        continue
                else:
                    # 只做协战50，但当前不是协战50任务 → 跳过
                    logger.info(f"[角色] {self.account_info}, 只做 [协战任务], [{self.task_type}], 跳过")
                    continue
            else:
                if task_type == TaskType.assist50:
                    # 不做协战50，但当前是协战50任务 → 跳过
                    logger.info(f"[角色] {self.account_info}, 不做 [{self.task_type}], 跳过")
                    continue

            match task_type:
                # 日常任务，判断是否今天已完成
                case TaskType.dailyTask:
                    if taskCompleteTime == str(now.date()):
                        logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                        continue
                # 周任务，判断是否本周已完成
                case TaskType.weekTask:
                    start_of_week = now.date() - timedelta(days=now.weekday())  # 计算当前周的起始日期（周一）
                    end_of_week = start_of_week + timedelta(days=6)             # 计算当前周的结束日期（周日）
                    taskCompleteTime_dt = datetime.strptime(taskCompleteTime, "%Y-%m-%d").date()  # 将 taskCompleteTime 转换为 datetime 对象
                    # 判断目标日期是否在当前周范围内 如果在说明本周运行过
                    if start_of_week <= taskCompleteTime_dt <= end_of_week:
                        logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                        continue
                # 限时任务，判断是否今天已完成
                case TaskType.limitTask:
                    if taskCompleteTime == str(now.date()):
                        logger.info(f"[角色] {self.account_info}, 已完成 [{self.task_type}], 跳过")
                        continue
                    else:
                        # ===== 判断是否已到限时任务执行时间（19:00）=====
                        now = datetime.now()
                        limit_hour = 19
                        if not (now.hour > limit_hour or (now.hour == limit_hour and now.minute >= 0)):
                            target_time = datetime(2099, 1, 1)
                            for task in self.config.waiting_task:
                                self.set_next_run(task=task.command, target=target_time)
                            # ===== 未到19点，等待并设置19点运行 =====
                            self.config.small_account.small_account_name.account_name = "未知角色"
                            self.config.save()
                            self.push_notify(content=f'[{self.task_type}]等待 {limit_hour}:00 运行')
                            self.set_next_run(task='SmallAccount', target=datetime.now().replace(hour=limit_hour, minute=0, second=0, microsecond=0))
                            raise TaskEnd('SmallAccount')

            # 上次完成时间
            logger.info(f"[角色] {self.account_info}, 上次 [{self.task_type}] 完成时间: {taskCompleteTime}")
            # 切换角色
            self.switch_account(con, current_account_data)
            # 设置角色任务
            self.set_task(current_account_data, all_accounts_data, task_type)

            self.set_next_run(task='SmallAccount', target=datetime.now() + timedelta(minutes=1))
            raise TaskEnd('SmallAccount')

    def switch_account(self, con, current_account_data):
        logger.info(f"[角色] {self.account_info}, 开始切换...")
        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            account_alias=current_account_data.get("accountAlias"),
            apple_or_android=current_account_data.get("appleOrAndroid"),
            character=current_account_data.get("character"),
            svr=current_account_data.get("svr"),
        )
        sa = SwitchAccount(self.config, self.device, toAccount)
        sa.switchAccount()
        con.small_account_name.account_name = self.account_info
        self.config.save()
        logger.info(f"[角色] {self.account_info}, 切换完成")
    
    def set_task(self, current_account_data, all_accounts_data, task_type):
        logger.info(f"[角色] {self.account_info}, 开始调起任务")
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
            # 周任务
            case TaskType.weekTask:
                for task in self.week_task:
                    self.set_next_run(task=task, target=target_time)
            # 协站50任务
            case TaskType.assist50:
                for task in self.assist50_run_task:
                    self.set_next_run(task=task, target=target_time)

        # 除了 assist50，其他任务类型都运行 always_run_task
        if task_type != TaskType.assist50:
            for task in self.always_run_task:
                self.set_next_run(task=task, target=target_time)

        # 更新日常任务完成时间，保存更新后的配置文件
        datetoday = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"[角色] {self.account_info}, 更新 {task_type}: {datetoday}")
        current_account_data[f"{task_type}"] = datetoday
        with open('config/SmallAccount/accounts.json', 'w', encoding='utf-8') as file:
            json.dump(all_accounts_data, file, ensure_ascii=False, indent=4)

        self.push_notify(content=f"{self.account_info}, [{self.task_type}]已创建")

    def all_account_complete_task(self, con):
        logger.hr("任务结束", 1)
        con.small_account_name.account_name = "未知角色"
        self.config.save()
        self.push_notify(content="✅ 所有角色任务均已完成")
        target_time = datetime(2099, 1, 1)
        for task in self.config.waiting_task:
            self.set_next_run(task=task.command, target=target_time)
        self.set_next_run(task='SmallAccount', success=True, finish=True)
        raise TaskEnd('SmallAccount')


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('switch')
    d = Device(c)
    t = ScriptTask(c, d)
    # t.run()

    # 批量修改任务时间
    c.get_next()
    target_time = datetime(2099, 1, 1)
    for task in c.pending_task:
        c.task_delay(task=task.command, target=target_time)
    c.task_delay(task="SmallAccount", target=datetime.now())

# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import datetime, timedelta
from enum import Enum
from module.exception import TaskEnd
from module.logger import logger
from tasks.SmallAccount.base_channel_task import BaseChannelTask

""" 小号切换 """


class TaskType(str, Enum):
    dailyTask = 'dailyTaskCompleteTime'
    limitTask = 'limitTaskCompleteTime'
    weekTask = 'weekTaskCompleteTime'
    assist50 = 'Assist50Time'


class ScriptTask(BaseChannelTask):
    # 跳过的任务
    skip_task = ['Restart', 'BackUp']
    # 周任务只在周一 运行
    week_task = ['RichMan', 'WeeklyTrifles']
    # 限时任务 晚上7点后运行
    limit_task = ['Hunt', 'DemonEncounter', 'CollectiveMissions']
    # 协站50运行的任务
    assist50_run_task = ['DailyTrifles', 'EvoZone']
    # 总是运行的任务
    always_run_task = ['KekkaiUtilize', 'TalismanPass']
    task_type = ''
    account_info = ''

    def run_4399(self, con, current_account_data, index):

        # ===== 执行日常任务 =====
        self.task_type = "日常任务"
        self.run_task(con, current_account_data, index, TaskType.dailyTask)

        # # ===== 执行协战任务 =====
        # self.task_type = "协战任务"
        # self.run_task(con, current_account_data, index, TaskType.assist50)

        # # ===== 执行周任务 =====
        # self.task_type = "周任务"
        # self.run_task(con, current_account_data, index, TaskType.weekTask)
        #
        # # ===== 执行限时任务 =====
        # self.task_type = "限时任务"
        # self.run_task(con, current_account_data, index, TaskType.limitTask)

    def run_task(self, con, current_account_data, index, task_type):
        logger.hr(f'{self.task_type}', 1)
        taskCompleteTime = current_account_data.get(f"{task_type}")

        now = datetime.now()

        self.account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"

        # 判断是否只做协站50任务
        if bool(current_account_data.get('isOnlyAssist50')):
            if task_type == TaskType.assist50:
                if taskCompleteTime == str(now.date()):
                    logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                    return
            else:
                # 只做协战50，但当前不是协战50任务 → 跳过
                logger.info(f"[角色] {self.account_info}, 只做 [协战任务], [{self.task_type}], 跳过")
                return
        else:
            if task_type == TaskType.assist50:
                # 不做协战50，但当前是协战50任务 → 跳过
                logger.info(f"[角色] {self.account_info}, 不做 [{self.task_type}], 跳过")
                return

        match task_type:
            # 日常任务，判断是否今天已完成
            case TaskType.dailyTask:
                if taskCompleteTime == str(now.date()):
                    logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                    return
                    # 周任务，判断是否本周已完成
            case TaskType.weekTask:
                start_of_week = now.date() - timedelta(days=now.weekday())  # 计算当前周的起始日期（周一）
                end_of_week = start_of_week + timedelta(days=6)             # 计算当前周的结束日期（周日）
                taskCompleteTime_dt = datetime.strptime(taskCompleteTime, "%Y-%m-%d").date()  # 将 taskCompleteTime 转换为 datetime 对象
                # 判断目标日期是否在当前周范围内 如果在说明本周运行过
                if start_of_week <= taskCompleteTime_dt <= end_of_week:
                    logger.info(f"[角色] {self.account_info}, 已完成[{self.task_type}], 跳过")
                    return
                    # 限时任务，判断是否今天已完成
            case TaskType.limitTask:
                if taskCompleteTime == str(now.date()):
                    logger.info(f"[角色] {self.account_info}, 已完成 [{self.task_type}], 跳过")
                    return
                else:
                    # ===== 判断是否已到限时任务执行时间（19:00）=====
                    now = datetime.now()
                    limit_hour = 19
                    if not (now.hour > limit_hour or (now.hour == limit_hour and now.minute >= 0)):
                        target_time = datetime(2099, 1, 1)
                        for task in self.config.waiting_task:
                            self.set_next_run(task=task.command, target=target_time)
                        # ===== 未到19点，等待并设置19点运行 =====
                        self.config.small_account.small_account_config.account_name = "未知角色"
                        self.config.save()
                        self.push_notify(content=f'[{self.task_type}]等待 {limit_hour}:00 运行')
                        self.set_next_run(task='SmallAccount', target=datetime.now().replace(hour=limit_hour, minute=0, second=0, microsecond=0))
                        raise TaskEnd('SmallAccount')

        # 上次完成时间
        logger.info(f"[角色] {self.account_info}, 上次 [{self.task_type}] 完成时间: {taskCompleteTime}")
        # 切换角色
        self.switch_account(con, current_account_data, index, task_type)
        # 设置角色任务
        self.set_task(con, current_account_data, index, task_type)

        self.set_next_run(task='SmallAccount', target=datetime.now() + timedelta(minutes=1))
        raise TaskEnd('SmallAccount')

    def set_task(self, con, current_account_data, index, task_type):
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

        for task in self.always_run_task:
            self.set_next_run(task=task, target=target_time)

        self.update_account_data(con, current_account_data, index, task_type)
        self.push_notify(content=f"{self.account_info} [{self.task_type}]创建")






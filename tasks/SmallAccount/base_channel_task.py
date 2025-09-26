from enum import Enum

import json
from module.logger import logger
from datetime import datetime, timedelta
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from module.exception import TaskEnd, SwitchAccountError
from tasks.GameUi.game_ui import GameUi


class TaskType(str, Enum):
    dailyTask = 'dailyTime'
    limitTask = 'limitTime'
    weekTask = 'weekTime'
    assist50 = 'assist50Time'


class BaseChannelTask(GameUi):
    # 提取两个子类的共同方法
    def run_task(self, con, current_account_data, index, task_type):
        pass

    def set_task(self, con, current_account_data, account_index, task_type):
        pass

    def switch_account(self, con, current_account_data, index, task_type):
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
            con.small_account_config.account_name = account_info
            self.config.save()
            logger.info(f"[角色] {account_info}, 切换完成")
        else:
            self.update_account_data(con, current_account_data, index, task_type)
            raise SwitchAccountError(f"[角色] {account_info}, 切换失败")

    def update_account_data(self, con, current_account_data, account_index, task_type):
        # 更新当前账号的完成时间
        datetoday = datetime.now().strftime("%Y-%m-%d")
        current_account_data[f"{task_type}"] = datetoday

        # 重新读取完整数据
        accounts_file = con.small_account_config.accounts_file
        with open(f'config/SmallAccount/{accounts_file}', 'r', encoding='utf-8') as file:
            all_accounts_data = json.load(file)

        # 更新指定索引位置的数据
        all_accounts_data[account_index] = current_account_data

        # 保存回文件
        with open(f'config/SmallAccount/{accounts_file}', 'w', encoding='utf-8') as file:
            json.dump(all_accounts_data, file, ensure_ascii=False, indent=4)

    def all_account_complete_task(self, con):
        logger.hr("任务结束", 1)
        con.small_account_config.account_name = "未知角色"
        self.config.save()

        target_time = datetime(2099, 1, 1)
        for task in self.config.waiting_task:
            self.set_next_run(task=task.command, target=target_time)

        self.set_next_run(task='SmallAccount', success=True, finish=True)
        self.push_notify(content="✅ 所有角色任务均已完成")
        raise TaskEnd('SmallAccount')

    def get_task_type_name(self, task_type: TaskType) -> str:
        mapping = {
            TaskType.dailyTask: "日常任务",
            TaskType.limitTask: "限时任务",
            TaskType.weekTask: "周任务",
            TaskType.assist50: "协战任务"
        }
        return mapping.get(task_type, "未知任务")

    def _handle_limit_task_wait(self, now, task_type_name):
        """检查是否到达限时任务执行时间（19:00后）"""
        limit_hour = 19
        if now.hour > limit_hour or (now.hour == limit_hour and now.minute >= 0):
            return  # 可以执行限时任务

        # 未到执行时间，设置等待
        target_time = datetime(2099, 1, 1)
        for task in self.config.waiting_task:
            self.set_next_run(task=task.command, target=target_time)

        self.config.small_account.small_account_config.account_name = "未知角色"
        self.config.save()
        self.push_notify(content=f'[{task_type_name}]等待 {limit_hour}:00 运行')
        self.set_next_run(task='SmallAccount', target=datetime.now().replace(hour=limit_hour, minute=0, second=0, microsecond=0))
        raise TaskEnd('SmallAccount')

    def _set_batch_tasks(self, task_list, target_time):
        """批量设置任务执行时间"""
        for task in task_list:
            self.set_next_run(task=task, target=target_time)

    def _is_task_completed(self, task_type, taskCompleteTime, now):
        """检查任务是否已完成"""
        match task_type:
            case TaskType.dailyTask:
                return taskCompleteTime == str(now.date())
            case TaskType.weekTask:
                start_of_week = now.date() - timedelta(days=now.weekday())
                end_of_week = start_of_week + timedelta(days=6)
                taskCompleteTime_dt = datetime.strptime(taskCompleteTime, "%Y-%m-%d").date()
                return start_of_week <= taskCompleteTime_dt <= end_of_week
            case TaskType.limitTask:
                return taskCompleteTime == str(now.date())
            case TaskType.assist50:
                return taskCompleteTime == str(now.date())
        return False

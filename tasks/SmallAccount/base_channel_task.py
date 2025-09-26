from enum import Enum

import json
from module.logger import logger
from datetime import datetime, timedelta
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from module.exception import TaskEnd, SwitchAccountError
from tasks.GameUi.game_ui import GameUi


class BaseChannelTask(GameUi):
    # 提取两个子类的共同方法
    def run_task(self, con, all_accounts_data, index, task_type):
        pass

    def set_task(self, con, current_account_data, account_index, task_type):
        pass

    def switch_account(self, con, current_account_data, index, task_type):
        account_info = f"{current_account_data.get('svr')}-{current_account_data.get('character')}"

        logger.info(f"[角色] {account_info}, 开始切换...")

        toAccount = AccountInfo(
            account=current_account_data.get("account"),
            password=current_account_data.get("password"),
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
        self.push_notify(content="✅ 所有角色任务均已完成")
        target_time = datetime(2099, 1, 1)
        for task in self.config.waiting_task:
            self.set_next_run(task=task.command, target=target_time)
        self.set_next_run(task='SmallAccount', success=True, finish=True)
        raise TaskEnd('SmallAccount')
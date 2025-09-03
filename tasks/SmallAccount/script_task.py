# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import json
from module.logger import logger
from datetime import datetime, timedelta
from tasks.Component.SwitchAccount.switch_account import SwitchAccount
from tasks.Component.SwitchAccount.switch_account_config import AccountInfo
from module.exception import TaskEnd
from tasks.GameUi.game_ui import GameUi

""" 小号切换 """
class ScriptTask(GameUi):
    def run(self):
        con = self.config.small_account

        logger.info('开始任务, 读取配置文件')
        # 假设配置文件路径为 config/accounts.json
        with open('config/SmallAccount/accounts.json', 'r', encoding='utf-8') as file:
            all_accounts = json.load(file)

        for index, account_data in enumerate(all_accounts):

            completeTime = account_data.get("completeTime")

            # 判断是否是今天的日期
            if completeTime == str(datetime.now().date()):
                logger.info(f"账号 [{account_data.get('character')}], 今天任务已完成, 跳过")
                if index == len(all_accounts) - 1:
                    logger.info('所有账号任务已完成')
                    con.small_account_name.name = "未知账号"
                    self.config.save()
                    for task in self.config.waiting_task:
                        self.set_next_run(task=task.command, target=datetime.now() + timedelta(days=7))
                    self.set_next_run(task='SmallAccount', success=True, finish=True)
                    raise TaskEnd('SmallAccount')
                continue
            else:
                logger.info(f"账号 {account_data.get('character')} 上次任务完成时间: {completeTime}")
                account_data["completeTime"] = datetime.now().strftime("%Y-%m-%d")

            logger.info(f"账号 {account_data.get('character')} 切换中...")
            toAccount = AccountInfo(
                account=account_data.get("account"),
                account_alias=account_data.get("accountAlias"),
                apple_or_android=account_data.get("appleOrAndroid"),
                character=account_data.get("character"),
                svr=account_data.get("svr"),
            )
            sa = SwitchAccount(self.config, self.device, toAccount)
            sa.switchAccount()
            con.small_account_name.name = account_data.get("character")
            self.config.save()
            logger.info(f"账号 {account_data.get('character')} 切换完成")

            logger.info(f"账号 {account_data.get('character')} 分配任务")
            for task in self.config.waiting_task:
                print(task.command)
                if task.command == 'Restart':
                    continue
                self.set_next_run(task=task.command, target=datetime.now())

            # 保存更新后的配置文件
            logger.info(f"账号 {account_data.get('character')} 更新完成时间: {datetime.now().strftime('%Y-%m-%d')}")
            with open('config/SmallAccount/accounts.json', 'w', encoding='utf-8') as file:
                json.dump(all_accounts, file, ensure_ascii=False, indent=4)

            self.set_next_run(task='SmallAccount', target=datetime.now() + timedelta(minutes=1))
            raise TaskEnd('SmallAccount')


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    c = Config('账号切换')
    d = Device(c)
    t = ScriptTask(c, d)
    t.run()


# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from tasks.ActivityCommon.challenge import ScriptTask as Battle
from tasks.ActivityCommon.delegate import ScriptTask as Delegate
from tasks.ActivityCommon.general import ScriptTask as General
from tasks.ActivityCommon.script_task import ScriptTask as ActivityCommonScriptTask
""" 活动通用2 """


class ScriptTask(ActivityCommonScriptTask):
    def __init__(self, config):
        super().__init__(config)
        self.Battle = Battle(self.config)
        self.General = General(self.config)
        self.Delegate = Delegate(self.config)

    def run(self):
        config = self.config.activity_common_2
        # 加载所有图片
        goto_challenge_folder = "./tasks/ActivityCommon2/gotoChallenge"
        battle_folder = "./tasks/ActivityCommon/战斗"

        self.General.run_config(config, goto_challenge_folder, battle_folder)


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('4399')
    t = ScriptTask(c)

    t.run()

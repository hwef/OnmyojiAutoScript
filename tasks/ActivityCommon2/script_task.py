# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from tasks.ActivityCommon.script_task import ScriptTask as ActivityCommonScriptTask
""" 活动通用2 """


class ScriptTask(ActivityCommonScriptTask):

    def run(self):
        config = self.config.activity_common_2
        # 加载所有图片
        goto_challenge_folder = "ActivityCommon2/gotoActivity"
        battle_folder = "ActivityCommon/战斗"
        self.run_config(config, goto_challenge_folder, battle_folder)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('switch')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()

# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from module.exception import TaskEnd
from tasks.ActivityCommon.challenge import ScriptTask as Battle
from tasks.ActivityCommon.delegate import ScriptTask as Delegate
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul

""" 活动通用 """


class ScriptTask(SwitchSoul, GeneralBattle):
    def __init__(self, config):
        super().__init__(config)
        self.Battle = Battle(self.config)
        self.Delegate = Delegate(self.config)

    def run(self):
        config = self.config.activity_common.activity_common_config
        if config.active_type == '战斗':
            self.Battle.run()
        elif config.active_type == '委派':
            self.Delegate.run()
        else:
            raise TaskEnd('no active_type')





if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('du')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()

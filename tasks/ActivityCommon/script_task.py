# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import os
import random
from datetime import datetime, timedelta, time
from module.atom.image import RuleImage
from module.exception import TaskEnd
from module.logger import logger
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_shikigami_records
from tasks.Restart.assets import RestartAssets
from tasks.ActivityCommon.battle import ScriptTask as Battle
from tasks.ActivityCommon.delegate import ScriptTask as Delegate

""" 活动通用 """


class ScriptTask(GameUi, SwitchSoul, GeneralBattle):
    def __init__(self, config, device):
        super().__init__(config, device)
        self.Battle = Battle(self.config, self.device)
        self.Delegate = Delegate(self.config, self.device)

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

    c = Config('wy')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()

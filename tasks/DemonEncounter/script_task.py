# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from enum import Enum
from cached_property import cached_property
from datetime import datetime, timedelta

from module.logger import logger
from module.exception import TaskEnd
from module.base.timer import Timer
from module.server.i18n import I18n

from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_demon_encounter, page_shikigami_records
from tasks.DemonEncounter.assets import DemonEncounterAssets
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.DemonEncounter.data.answer import Answer
from tasks.Component.GeneralBuff.config_buff import BuffClass


class LanternClass(Enum):
    BATTLE = 0  # 打怪  --> 无法判断因为怪的图片不一样，用排除法
    BOX = 1  # 开宝箱
    MAIL = 2  # 邮件答题
    REALM = 3  # 打结界
    EMPTY = 4  # 空
    MYSTERY = 5  # 神秘任务
    BOSS = 6  # 大鬼王


class ScriptTask(GameUi, GeneralBattle, DemonEncounterAssets, SwitchSoul):

    def run(self):
        if not self.check_time():
            logger.warning('Time is not right')
            raise TaskEnd('DemonEncounter')
        self.ui_get_current_page()
        self.ui_goto(page_shikigami_records)

        # 切换通用御魂
        self.run_switch_soul(self.config.demon_encounter.switch_soul.switch_group_team)

        # 根据周几切换指定御魂
        soul_config = self.config.demon_encounter.demon_soul_config
        best_soul_config = self.config.demon_encounter.best_demon_soul_config
        if soul_config.enable or best_soul_config.enable:
            self.ui_goto(page_shikigami_records)
            self.checkout_soul()

        self.ui_goto(page_demon_encounter)
        self.execute_lantern()
        self.execute_boss()

        self.set_next_run(task='DemonEncounter', success=True, finish=False)
        raise TaskEnd('DemonEncounter')

    def checkout_soul(self):
        """
        切换御魂
        """
        # 判断今天是周几
        today = datetime.now().weekday()

        # 普通逢魔御魂
        soul_config = self.config.demon_encounter.demon_soul_config
        # 极逢魔御魂
        best_soul_config = self.config.demon_encounter.best_demon_soul_config

        # 极逢魔选择
        best_demon_boss_config = self.config.demon_encounter.best_demon_boss_config

        group, team = None, None
        if today == 0:
            # 获取group,team
            if best_soul_config.enable and best_demon_boss_config.best_demon_kiryou_select:
                group, team = best_soul_config.best_demon_kiryou_utahime.split(",")
            else:
                group, team = soul_config.demon_kiryou_utahime.split(",")
        elif today == 1:
            if best_soul_config.enable and best_demon_boss_config.best_demon_shinkirou_select:
                group, team = best_soul_config.best_demon_shinkirou.split(",")
            else:
                group, team = soul_config.demon_shinkirou.split(",")
        elif today == 2:
            if best_soul_config.enable and best_demon_boss_config.best_demon_tsuchigumo_select:
                group, team = best_soul_config.best_demon_tsuchigumo.split(",")
            else:
                group, team = soul_config.demon_tsuchigumo.split(",")
        elif today == 3:
            if best_soul_config.enable and best_demon_boss_config.best_demon_gashadokuro_select:
                group, team = best_soul_config.best_demon_gashadokuro.split(",")
            else:
                group, team = soul_config.demon_gashadokuro.split(",")
        elif today == 4:
            if best_soul_config.enable and best_demon_boss_config.best_demon_namazu_select:
                group, team = best_soul_config.best_demon_namazu.split(",")
            else:
                group, team = soul_config.demon_namazu.split(",")
        elif today == 5:
            group, team = soul_config.demon_oboroguruma.split(",")
        elif today == 6:
            group, team = soul_config.demon_nightly_aramitama.split(",")
        if group and team:
            self.run_switch_soul_by_name(group, team)
        if today == 0:
            # 获取group,team
            if best_soul_config.enable and best_demon_boss_config.best_demon_kiryou_select:
                group, team = best_soul_config.best_demon_kiryou_utahime_supplementary.split(",")
            else:
                group, team = soul_config.demon_kiryou_utahime_supplementary.split(",")
            self.run_switch_soul_by_name(group, team)

    boss_count = 0

    def execute_boss(self):
        """
        打boss
        :return:
        """
        logger.hr('Start boss battle', 1)
        # 判断今天是周几
        today = datetime.now().weekday()
        wait_timer = Timer(60)
        wait_timer.start()
        while 1:
            self.screenshot()

            # 等待超时
            if wait_timer.reached():
                # self.push_notify(content=f"逢魔Boss 搜寻超时...")
                wait_timer.reset()
                break

            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                current, remain, total = self.O_DE_BOSS_PEOPLE.ocr(self.device.image)
                if total == 300 and current >= 260:
                    logger.info('Boss battle people is full')
                    if not self.appear(self.I_UI_BACK_RED):
                        logger.warning('Boss battle people is full but no red back')
                        continue
                    self.ui_click_until_disappear(self.I_UI_BACK_RED)
                    # 退出重新选一个没满员的boss
                    logger.info('Exit and reselect')
                    continue
                else:
                    logger.info('Boss battle people is not full')
                    break

            if self.config.demon_encounter.best_demon_boss_config.enable and today < 5:
                if self.appear_then_click(self.I_DE_BOSS_BEST, interval=4):
                    continue
            else:
                if self.appear_then_click(self.I_DE_BOSS, interval=4):
                    continue

            if self.appear_then_click(self.I_BOSS_NAMAZU, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_SHINKIRO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_ODOKURO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_OBOROGURUMA, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_TSUCHIGUMO, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_SONGSTRESS, interval=1):
                continue

            if self.click(self.C_DM_BOSS_CLICK, interval=1.7):
                continue

        logger.info('Boss battle start')
        # 点击集结挑战
        boss_fire_count = 0  # 五次没点到就意味着今天已经挑战过了
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_CONFIRM):
                self.ui_click(self.I_BOSS_NO_SELECT, self.I_BOSS_SELECTED)
                self.ui_click(self.I_BOSS_CONFIRM, self.I_BOSS_GATHER)
                break
            if self.appear(self.I_BOSS_GATHER):
                break
            if boss_fire_count >= 5:
                logger.warning('Boss battle already done')
                # self.push_notify(content=f"封魔BOSS, 5次点击未进入...")
                self.ui_click_until_disappear(self.I_UI_BACK_RED)
                logger.info('重新选择封魔BOSS')
                # self.push_notify(content=f"重新选择封魔BOSS...")
                if self.boss_count <= 3:
                    self.boss_count += 1
                    self.execute_boss()
                return
            if self.appear_then_click(self.I_BOSS_FIRE, interval=3) or self.appear_then_click(self.I_BEST_BOSS_FIRE,
                                                                                              interval=3):
                boss_fire_count += 1
                continue
        logger.info('Boss battle confirm and enter')
        # 等待挑战, 5秒也是等
        time.sleep(5)
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.wait_until_disappear(self.I_BOSS_GATHER)
        self.device.stuck_record_clear()
        self.device.stuck_record_add('BATTLE_STATUS_S')
        # 延长时间并在战斗结束后改回来
        self.device.stuck_timer_long = Timer(480, count=480).start()
        config = self.con
        self.run_general_battle(config)
        self.device.stuck_timer_long = Timer(300, count=300).start()

        # 等待回到挑战boss主界面
        self.wait_until_appear(self.I_BOSS_GATHER)
        while 1:
            self.screenshot()
            if self.appear(self.I_DE_LOCATION):
                break
            if self.appear_then_click(self.I_UI_CONFIRM_SAMLL, interval=1):
                continue
            if self.appear_then_click(self.I_BOSS_BACK_WHITE, interval=1):
                continue
        # 返回到封魔主界面

    def execute_lantern(self):
        """
        点灯笼 四次
        :return:
        """
        # 先点四次
        ocr_timer = Timer(0.8)
        ocr_timer.start()
        while 1:
            self.screenshot()
            if not ocr_timer.reached():
                continue
            else:
                ocr_timer.reset()
            cu, re, total = self.O_DE_COUNTER.ocr(self.device.image)
            if cu + re != total:
                logger.warning('Lantern count error')
                continue
            if cu == 0 and re == 4:
                break

            if self.appear_then_click(self.I_DE_FIND, interval=2.5):
                continue
        logger.info('Lantern count success')
        # 然后领取红色达摩
        self.screenshot()
        if not self.appear(self.I_DE_AWARD):
            self.ui_get_reward(self.I_DE_RED_DHARMA)
        self.wait_until_appear(self.I_DE_AWARD)
        # 然后到四个灯笼
        match_click = {
            1: self.C_DE_1,
            2: self.C_DE_2,
            3: self.C_DE_3,
            4: self.C_DE_4,
        }
        for i in range(1, 5):
            logger.hr(f'Check lantern {i}', 3)
            lantern_type = self.check_lantern(i)
            match lantern_type:
                case LanternClass.BOX:
                    self._box(match_click[i])
                case LanternClass.MAIL:
                    self._mail(match_click[i])
                case LanternClass.REALM:
                    self._realm(match_click[i])
                case LanternClass.EMPTY:
                    logger.warning(f'Lantern {i} is empty')
                case LanternClass.BATTLE:
                    self._battle(match_click[i])
                case LanternClass.MYSTERY:
                    self._mystery(match_click[i])
                case LanternClass.BOSS:
                    self._boss(match_click[i])
            time.sleep(1)

    @cached_property
    def con(self) -> GeneralBattleConfig:
        return GeneralBattleConfig()

    def check_lantern(self, index: int = 1):
        """
        检查灯笼的类型
        :param index: 四个灯笼，从1开始
        :return:
        """
        match_roi = {
            1: self.C_DE_1.roi_front,
            2: self.C_DE_2.roi_front,
            3: self.C_DE_3.roi_front,
            4: self.C_DE_4.roi_front,
        }
        match_empty = {
            1: self.I_DE_DEFEAT_1,
            2: self.I_DE_DEFEAT_2,
            3: self.I_DE_DEFEAT_3,
            4: self.I_DE_DEFEAT_4,
        }
        self.I_DE_BOX.roi_back = match_roi[index]
        self.I_DE_LETTER.roi_back = match_roi[index]
        self.I_DE_MYSTERY.roi_back = match_roi[index]
        self.I_DE_REALM.roi_back = match_roi[index]
        self.I_DE_FIND_BOSS.roi_back = match_roi[index]
        target_box = self.I_DE_BOX
        target_letter = self.I_DE_LETTER
        target_mystery = self.I_DE_MYSTERY
        target_realm = self.I_DE_REALM
        target_find_boss = self.I_DE_FIND_BOSS
        target_empty = match_empty[index]

        # 开始判断
        self.screenshot()
        if self.appear(target_box):
            logger.info(f'Lantern {index} is box')
            return LanternClass.BOX
        elif self.appear(target_letter):
            logger.info(f'Lantern {index} is mail')
            return LanternClass.MAIL
        elif self.appear(target_mystery):
            logger.info(f'Lantern {index} is mystery task')
            return LanternClass.MYSTERY
        elif self.appear(target_realm):
            logger.info(f'Lantern {index} is realm')
            return LanternClass.REALM
        elif self.appear(target_empty):
            logger.info(f'Lantern {index} is empty')
            return LanternClass.EMPTY
        elif self.appear(target_find_boss):
            logger.info(f'Lantern {index} is boss')
            return LanternClass.BOSS
        else:
            # 无法判断是否是战斗的还是结界的
            logger.info(f'Lantern {index} is battle')
            return LanternClass.BATTLE

    def _box(self, target_click):
        while 1:
            self.screenshot()
            if self.appear(self.I_JADE_50):
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_UI_BACK_RED)
                continue
            if self.click(target_click, interval=1):
                continue
        while 1:
            self.screenshot()
            if self.appear(self.I_BLUE_PIAO):
                if self.click(self.I_JADE_50):
                    logger.info('Buy a mystery amulet for 50 jade')
                    continue
            if not self.appear(self.I_BLUE_PIAO):
                if self.appear_then_click(self.I_DE_FIND, interval=2.5):
                    break

    def _mail(self, target_click):
        # 答题
        def answer():
            click_match = {
                1: self.C_ANSWER_1,
                2: self.C_ANSWER_2,
                3: self.C_ANSWER_3,
            }
            index = None
            self.screenshot()
            question = self.O_LETTER_QUESTION.detect_text(self.device.image)
            question = question.replace('?', '').replace('？', '')
            answer_1 = self.O_LETTER_ANSWER_1.detect_text(self.device.image)
            answer_2 = self.O_LETTER_ANSWER_2.detect_text(self.device.image)
            answer_3 = self.O_LETTER_ANSWER_3.detect_text(self.device.image)
            if answer_1 == '其余选项皆对':
                index = 1
            elif answer_2 == '其余选项皆对':
                index = 2
            elif answer_3 == '其余选项皆对':
                index = 3
            if not index:
                index = Answer().answer_one(question=question, options=[answer_1, answer_2, answer_3])
            if index is None:
                index = 1
            logger.info(f'Question: {question}, Answer: {index}')
            return click_match[index]

        while 1:
            self.screenshot()
            if self.appear(self.I_LETTER_CLOSE):
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_UI_BACK_RED)
                continue
            if self.click(target_click, interval=1):
                continue
        logger.info('Question answering Start')
        for i in range(1, 4):
            # 还未测试题库无法识别的情况
            logger.hr(f'Answer {i}', 3)
            answer_click = answer()
            # self.ui_get_reward(answer())
            while 1:
                self.screenshot()
                if self.ui_reward_appear_click():
                    time.sleep(0.5)
                    while 1:
                        self.screenshot()
                        # 等待动画结束
                        if not self.appear(self.I_UI_REWARD, threshold=0.6):
                            logger.info('Get reward success')
                            break
                        # 一直点击
                        if self.ui_reward_appear_click():
                            continue
                    break
                # 如果没有出现红色关闭按钮，说明答题结束
                if not self.appear(self.I_LETTER_CLOSE) and not self.appear(self.I_MALL) and not self.appear(self.I_DE_LETTER):
                    time.sleep(1)
                    self.screenshot()
                    if self.appear(self.I_LETTER_CLOSE) or self.appear(self.I_MALL) or self.appear(self.I_DE_LETTER):
                        continue
                    else:
                        # self.save_image()
                        logger.warning('Answer finish')
                        return

                # 一直点击
                self.click(answer_click, interval=1)
                time.sleep(0.5)
                self.appear_then_click(self.I_DE_FIND, interval=1)
            time.sleep(0.5)

    def _battle(self, target_click):
        config = self.con
        while 1:
            self.screenshot()
            if not self.appear(self.I_DE_LOCATION):
                logger.info('Battle Start')
                break
            if self.appear(self.I_DE_SMALL_FIRE):
                # 小鬼王
                logger.info('Small Boss')
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_DE_SMALL_FIRE):
                        break
                    if self.appear_then_click(self.I_DE_SMALL_FIRE, interval=1):
                        continue
                break

            if self.click(target_click, interval=1):
                continue
        if self.run_general_battle(config):
            logger.info('Battle End')

    def _realm(self, target_click):
        # 结界
        config = self.con
        while 1:
            self.screenshot()
            if not self.appear(self.I_DE_LOCATION):
                logger.info('Battle Start')
                break
            if self.appear(self.I_BOSS_FIRE) or self.appear(self.I_BEST_BOSS_FIRE):
                self.appear_then_click(self.I_UI_BACK_RED)
                continue
            if self.appear_then_click(self.I_DE_REALM_FIRE, interval=0.7):
                continue

            if self.click(target_click, interval=1):
                continue
        if self.run_general_battle(config):
            logger.info('Battle End')

    def _mystery(self, target_click):
        # 神秘任务， 不做
        pass

    def _boss(self, target_click):
        # 运气爆表，点灯笼出现大鬼王
        while 1:
            self.screenshot()
            if self.appear(self.I_BOSS_KILLED):
                # 这个大鬼王已经击败
                logger.warning('Boss already killed')
                self.ui_click_until_disappear(self.I_UI_BACK_RED)
                break
            if self.appear(self.I_BOSS_FIRE):
                self.execute_boss()
                break
            if self.click(target_click, interval=2.3):
                continue

    def check_time(self):
        now = datetime.now()

        server_update = self.config.demon_encounter.scheduler.server_update
        target_time = datetime(now.year, now.month, now.day, server_update.hour, server_update.minute, server_update.second)

        if now.hour < 17:
            logger.info(f'Before 17:00, waiting until {target_time.strftime("%Y-%m-%d %H:%M:%S")} (today)')
            self.set_next_run(task='DemonEncounter', success=False, finish=False, target=target_time)
            return False
        elif now.hour >= 23:
            target_time += timedelta(days=1)  # Set to next day's 19:00
            logger.info(f'After 23:00, waiting until {target_time.strftime("%Y-%m-%d %H:%M:%S")} (next day)')
            self.set_next_run(task='DemonEncounter', success=False, finish=False, target=target_time)
            return False
        else:
            return True

    def run_general_battle(self, config: GeneralBattleConfig = None, buff: BuffClass or list[BuffClass] = None) -> bool:
        """
        运行脚本
        :return:
        """
        # 本人选择的策略是只要进来了就算一次，不管是不是打完了
        logger.hr("General battle start", 2)
        self.current_count += 1
        logger.info(f'Current tasks: {I18n.trans_zh_cn(self.config.task.command)}')
        logger.info(f'Current count: {self.current_count} / {self.limit_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'Current times: {task_run_time_seconds} / {self.limit_time}')

        if config is None:
            config = GeneralBattleConfig()

        win = self.battle_wait(config.random_click_swipt_enable)
        if win:
            return True
        else:
            return False

    def battle_wait(self, random_click_swipt_enable: bool) -> bool:
        # 重写
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 战斗过程 随机点击和滑动 防封
        logger.info("Start battle process")
        check_timer = None
        while 1:
            self.screenshot()

            if self.appear_then_click(self.I_PREPARE_HIGHLIGHT):
                time.sleep(1)
                self.device.stuck_record_add('BATTLE_STATUS_S')
                continue
            if self.appear(self.I_DE_WIN):
                logger.info('Appear [demon encounter] win button')
                self.ui_click_until_disappear(self.I_DE_WIN)
                check_timer = Timer(3)
                check_timer.start()
                continue
            if self.appear_then_click(self.I_WIN, interval=1):
                logger.info('Appear win button')
                check_timer = Timer(3)
                check_timer.start()
                continue
            if self.appear(self.I_REWARD):
                logger.info('Win battle')
                self.ui_click_until_disappear(self.I_REWARD)
                return True

            # 失败的
            if self.appear(self.I_FALSE):
                logger.warning('False battle')
                self.ui_click_until_disappear(self.I_FALSE)
                return False
            # 时间到
            if check_timer and check_timer.reached():
                logger.warning('Obtain battle timeout')
                return True


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('mi')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
    # t.battle_wait(True)

# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
from cached_property import cached_property
from datetime import timedelta, datetime

from module.base.timer import Timer
from module.atom.image_grid import ImageGrid
from module.logger import logger
from module.exception import TaskEnd

from tasks.GameUi.game_ui import GameUi
from tasks.Utils.config_enum import ShikigamiClass
from tasks.KekkaiUtilize.assets import KekkaiUtilizeAssets
from tasks.KekkaiUtilize.config import UtilizeRule, SelectFriendList
from tasks.KekkaiUtilize.utils import CardClass, target_to_card_class
from tasks.Component.ReplaceShikigami.replace_shikigami import ReplaceShikigami
from tasks.GameUi.page import page_main, page_guild

""" 结界蹭卡 """


class ScriptTask(GameUi, ReplaceShikigami, KekkaiUtilizeAssets):
    last_best_index = 99
    utilize_erroe_num = 0

    def run(self):
        con = self.config.kekkai_utilize.utilize_config
        self.ui_get_current_page()
        self.ui_goto(page_guild)

        # 进入寮结界
        self.goto_realm()
        # 查看满级
        self.check_max_lv(con.shikigami_class)
        # 顺带收体力盒子或者是经验盒子
        time.sleep(1)
        self.check_box_ap_or_exp(con.box_ap_enable, con.box_exp_enable, con.box_exp_waste)

        # 在寮结界界面检查是否有收获 收体力或者资金
        self.check_utilize_harvest()

        # 育成界面去蹭卡
        self.check_utilize_add()

        for i in range(1, 5):
            self.ui_goto(page_guild)
            # 在寮的主界面 检查是否有收取体力或者是收取寮资金
            if self.check_guild_ap_or_assets(ap_enable=con.guild_ap_enable, assets_enable=con.guild_assets_enable):
                logger.warning(f'第[{i}]次检查寮收获,成功')
                self.ui_goto(page_main)
                break
            else:
                logger.warning(f'第[{i}]次检查寮收获寮收获,失败')
            self.ui_goto(page_main)

        raise TaskEnd

    def check_utilize_add(self):
        con = self.config.kekkai_utilize.utilize_config
        while 1:
            if self.utilize_erroe_num >= 3:
                logger.warning('Utilize error more than 3 times, exit')
                self.config.notifier.push(title=self.config.task.command, content=f"没有合适可以蹭的卡, 5分钟后再次执行蹭卡")
                self.set_next_run(task='KekkaiUtilize', target=datetime.now() + timedelta(minutes=5))
                return
            # 进入寮结界
            self.goto_realm()

            # 无论收不收到菜，都会进入看看至少看一眼时间还剩多少
            time.sleep(0.5)
            # 进入育成界面
            self.realm_goto_grown()
            self.screenshot()

            if not self.appear(self.I_UTILIZE_ADD):
                remaining_time = self.O_UTILIZE_RES_TIME.ocr(self.device.image)
                if not isinstance(remaining_time, timedelta):
                    logger.warning('Ocr remaining time error')
                logger.info(f'Utilize remaining time: {remaining_time}')
                # 已经蹭上卡了，设置下次蹭卡时间
                next_time = datetime.now() + remaining_time
                self.set_next_run(task='KekkaiUtilize', target=next_time)
                self.back_guild()
                return
            if not self.grown_goto_utilize():
                logger.info('Utilize failed, exit')
            self.run_utilize(con.select_friend_list, con.shikigami_class, con.shikigami_order)
            self.back_guild()

    def check_max_lv(self, shikigami_class: ShikigamiClass = ShikigamiClass.N):
        """
        在结界界面，进入式神育成，检查是否有满级的，如果有就换下一个
        退出的时候还是结界界面
        :return:
        """
        self.realm_goto_grown()
        if self.appear(self.I_RS_LEVEL_MAX):
            # 存在满级的式神
            logger.info('Exist max level shikigami and replace it')
            self.unset_shikigami_max_lv()
            self.switch_shikigami_class(shikigami_class)
            self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)
        else:
            logger.info('No max level shikigami')
        if self.detect_no_shikigami():
            logger.warning('There are no any shikigami grow room')
            self.switch_shikigami_class(shikigami_class)
            self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)

        # 回到结界界面
        while 1:
            self.screenshot()

            if self.appear(self.I_REALM_SHIN) and self.appear(self.I_SHI_GROWN):
                self.screenshot()
                if not self.appear(self.I_REALM_SHIN):
                    continue
                break
            if self.appear_then_click(self.I_UI_BACK_BLUE, interval=2.5):
                continue

    def check_guild_ap_or_assets(self, ap_enable: bool = True, assets_enable: bool = True) -> bool:
        """
        在寮的主界面 检查是否有收取体力或者是收取寮资金
        如果有就顺带收取
        :return:
        """
        # if ap_enable or assets_enable:
        #     self.screenshot()
        #     if not self.appear(self.I_GUILD_AP) and not self.appear(self.I_GUILD_ASSETS):
        #         logger.info('No ap or assets to collect')
        #         return False
        # else:
        #     return False

        # 如果有就收取
        timer_check = Timer(2)
        timer_check.start()
        while 1:
            self.screenshot()

            # 获得奖励
            if self.ui_reward_appear_click():
                timer_check.reset()

            # 资金收取确认
            if self.appear_then_click(self.I_GUILD_ASSETS_RECEIVE, interval=0.5):
                timer_check.reset()
                continue

            # 收体力
            if self.appear_then_click(self.I_GUILD_AP, interval=1.5):
                # 等待1秒，看到获得奖励
                time.sleep(1)
                # self.save_image()
                logger.info('appear_click guild_ap success')
                if self.ui_reward_appear_click(True):
                    logger.info('appear_click reward success')
                    # self.save_image()
                    timer_check.reset()
                    return True
                continue
            # 收资金
            if self.appear_then_click(self.I_GUILD_ASSETS, interval=1.5, threshold=0.6):
                timer_check.reset()
                continue

            if timer_check.reached():
                break
        return False

    def goto_realm(self):
        """
        从寮的主界面进入寮结界
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_REALM_SHIN):
                break
            if self.appear(self.I_SHI_DEFENSE):
                break

            if self.appear_then_click(self.I_GUILD_REALM, interval=1):
                continue

    def check_box_ap_or_exp(self, ap_enable: bool = True, exp_enable: bool = True, exp_waste: bool = True) -> bool:
        """
        顺路检查盒子
        :param ap_enable:
        :param exp_enable:
        :return:
        """

        # 退出到寮结界
        def _exit_to_realm():
            # 右上方关闭红色
            while 1:
                self.screenshot()
                if self.appear(self.I_REALM_SHIN):
                    break
                if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                    continue

        # 先是体力盒子
        def _check_ap_box(appear: bool = False):
            if not appear:
                return False
            # 点击盒子
            timer_ap = Timer(6)
            timer_ap.start()
            while 1:
                self.screenshot()

                if self.appear(self.I_UI_REWARD):
                    while 1:
                        self.screenshot()
                        if not self.appear(self.I_UI_REWARD):
                            break
                        if self.appear_then_click(self.I_UI_REWARD, self.C_UI_REWARD, interval=1, threshold=0.6):
                            continue
                    logger.info('Reward box')
                    break

                if self.appear_then_click(self.I_BOX_AP, interval=1):
                    continue
                if self.appear_then_click(self.I_AP_EXTRACT, interval=2):
                    continue
                if timer_ap.reached():
                    logger.warning('Extract ap box timeout')
                    break
            logger.info('Extract AP box finished')
            _exit_to_realm()

        # 经验盒子
        def _check_exp_box(appear: bool = False):
            if not appear:
                logger.info('No exp box')
                return False

            time_exp = Timer(12)
            time_exp.start()
            while 1:
                self.screenshot()
                # 如果出现结界皮肤， 表示收取好了
                if self.appear(self.I_REALM_SHIN) and not self.appear(self.I_BOX_EXP, threshold=0.6):
                    break
                # 如果出现收取确认，表明进入到了有满级的
                if self.appear(self.I_UI_CONFIRM):
                    self.screenshot()
                    if not self.appear(self.I_UI_CANCEL):
                        logger.info('No cancel button')
                        continue
                    if exp_waste:
                        check_button = self.I_UI_CONFIRM
                    else:
                        check_button = self.I_UI_CANCEL
                    while 1:
                        self.screenshot()
                        if not self.appear(check_button):
                            break
                        if self.appear_then_click(check_button, interval=1):
                            continue
                    break

                if self.appear(self.I_EXP_EXTRACT):
                    # 如果达到今日领取的最大，就不领取了
                    cur, res, totol = self.O_BOX_EXP.ocr(self.device.image)
                    if cur == res == totol == 0:
                        continue
                    if cur == totol and cur + res == totol:
                        logger.info('Exp box reach max do not collect')
                        break
                if self.appear_then_click(self.I_BOX_EXP, threshold=0.6, interval=1):
                    continue
                if self.appear_then_click(self.I_EXP_EXTRACT, interval=1):
                    continue

                if time_exp.reached():
                    logger.warning('Extract exp box timeout')
                    break
            _exit_to_realm()

        self.screenshot()
        box_ap = self.appear(self.I_BOX_AP)
        box_exp = self.appear(self.I_BOX_EXP, threshold=0.6) or self.appear(self.I_BOX_EXP_MAX, threshold=0.6)
        if ap_enable:
            _check_ap_box(box_ap)
        if exp_enable:
            _check_exp_box(box_exp)

    def check_utilize_harvest(self) -> bool:
        """
        在寮结界界面检查是否有收获
        :return: 如果没有返回False, 如果有就收菜返回True
        """
        self.screenshot()
        appear = self.appear(self.I_UTILIZE_EXP)
        if not appear:
            logger.info('No utilize harvest')
            return False

        # 收获
        self.ui_get_reward(self.I_UTILIZE_EXP)
        return True

    def realm_goto_grown(self):
        """
        进入式神育成界面
        :return:
        """
        while 1:
            self.screenshot()

            if self.in_shikigami_growth():
                break

            if self.appear_then_click(self.I_SHI_GROWN, interval=1):
                continue
        logger.info('Enter shikigami grown')

    def grown_goto_utilize(self):
        """
        从式神育成界面到 蹭卡界面
        :return:
        """
        self.screenshot()
        if not self.appear(self.I_UTILIZE_ADD):
            logger.warning('No utilize add')
            return False

        while 1:
            self.screenshot()

            if self.appear(self.I_U_ENTER_REALM):
                break
            if self.appear_then_click(self.I_UTILIZE_ADD, interval=2):
                continue
        logger.info('Enter utilize')
        return True

    def switch_friend_list(self, friend: SelectFriendList = SelectFriendList.SAME_SERVER) -> bool:
        """
        切换不同的服务区
        :param friend:
        :return:
        """
        logger.info('Switch friend list to %s', friend)
        if friend == SelectFriendList.SAME_SERVER:
            check_image = self.I_UTILIZE_FRIEND_GROUP
        else:
            check_image = self.I_UTILIZE_ZONES_GROUP

        timer_click = Timer(1)
        timer_click.start()
        while 1:
            self.screenshot()
            if self.appear(check_image):
                break
            if timer_click.reached():
                timer_click.reset()
                x, y = check_image.coord()
                self.device.click(x=x, y=y, control_name=check_image.name)
        if friend == SelectFriendList.DIFFERENT_SERVER:
            time.sleep(1)
        time.sleep(0.5)

    @cached_property
    def order_targets(self) -> ImageGrid:
        rule = self.config.kekkai_utilize.utilize_config.utilize_rule
        if rule == UtilizeRule.DEFAULT:
            return ImageGrid([self.I_U_FISH_6, self.I_U_TAIKO_6, self.I_U_FISH_5, self.I_U_TAIKO_5,
                              self.I_U_TAIKO_4, self.I_U_FISH_4, self.I_U_TAIKO_3, self.I_U_FISH_3])
        elif rule == UtilizeRule.FISH:
            return ImageGrid([self.I_U_FISH_6, self.I_U_FISH_5,
                              self.I_U_TAIKO_6, self.I_U_TAIKO_5, self.I_U_FISH_4, self.I_U_TAIKO_4,  self.I_U_FISH_3,self.I_U_TAIKO_3])
        elif rule == UtilizeRule.TAIKO:
            return ImageGrid([self.I_U_TAIKO_6, self.I_U_TAIKO_5,
                              self.I_U_FISH_6, self.I_U_FISH_5,  self.I_U_TAIKO_4, self.I_U_FISH_4, self.I_U_TAIKO_3,self.I_U_FISH_3])
        else:
            logger.error('Unknown utilize rule')
            raise ValueError('Unknown utilize rule')

    @cached_property
    def order_cards(self) -> list[CardClass]:
        rule = self.config.kekkai_utilize.utilize_config.utilize_rule
        result = []
        if rule == UtilizeRule.DEFAULT:
            result = [CardClass.FISH6, CardClass.TAIKO6,  CardClass.FISH5, CardClass.TAIKO5,
                      CardClass.TAIKO4, CardClass.FISH4, CardClass.TAIKO3, CardClass.FISH3]
        elif rule == UtilizeRule.FISH:
            result = [CardClass.FISH6, CardClass.FISH5,
                      CardClass.TAIKO6, CardClass.TAIKO5, CardClass.FISH4,CardClass.TAIKO4,  CardClass.FISH3,CardClass.TAIKO3]
        elif rule == UtilizeRule.TAIKO:
            result = [CardClass.TAIKO6, CardClass.TAIKO5,
                      CardClass.FISH6, CardClass.FISH5, CardClass.TAIKO4,CardClass.FISH4,  CardClass.TAIKO3,CardClass.FISH3]
        else:
            logger.error('Unknown utilize rule')
            raise ValueError('Unknown utilize rule')
        return result

    def run_utilize(self, friend: SelectFriendList = SelectFriendList.SAME_SERVER,
                    shikigami_class: ShikigamiClass = ShikigamiClass.N,
                    shikigami_order: int = 7):
        """
        执行寄养
        :param shikigami_class:
        :param friend:
        :param rule:
        :return:
        """

        def _current_select_best(last_best):
            """
            当前选中的最好的卡,(会自动和记录的最好的比较)
            包括点击这种卡
            :return: 返回当前选中的最好的卡， 如果什么的都没有，返回None
            """
            self.screenshot()
            target = self.order_targets.find_anyone(self.device.image)
            if target is None:
                logger.info('No target card found')
                return None
            card_class = target_to_card_class(target)
            self.last_best_index = self.order_cards.index(card_class)

            logger.info('Current find best card: %s', target)
            # 如果当前的卡比记录的最好的卡还要好,那么就更新最好的卡
            if last_best is not None:
                last_index = self.order_cards.index(last_best)
                current_index = self.order_cards.index(card_class)

                if current_index > last_index:
                    # 不比上一张卡好就退出不执行操作
                    logger.info('Current card is not better than last best card')
                    self.last_best_index = last_best
                    return last_best
            logger.info('Current select card: %s', card_class)

            # 选择这个卡
            self.appear_then_click(target, interval=1)
            time.sleep(1)
            # 验证这张卡 的等级是否一致
            # while 1:
            #     self.screenshot()
            return card_class

        logger.hr('Start utilize')
        self.switch_friend_list(friend)
        self.swipe(self.S_U_END, interval=3)
        if friend == SelectFriendList.SAME_SERVER:
            self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
            self.switch_friend_list(SelectFriendList.SAME_SERVER)
        else:
            self.switch_friend_list(SelectFriendList.SAME_SERVER)
            self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
        card_best = None
        swipe_count = 0
        while 1:
            self.screenshot()
            current_card = _current_select_best(card_best)

            if current_card is None:
                self.utilize_erroe_num += 1
                logger.warning('No card found')
                self.config.notifier.push(title=self.config.task.command, content=f"没有合适可以蹭的卡")
                return
            elif current_card == CardClass.TAIKO6 or current_card == CardClass.TAIKO5:
                card_num = self.check_card_num('勾玉')
                if card_num >= 76:
                    break
                if card_num >= 67:
                    break
            elif current_card == CardClass.FISH6 or current_card == CardClass.FISH5:
                card_num = self.check_card_num('体力')
                if card_num >= 151:
                    break
                if card_num >= 143:
                    break
                if card_num >= 134:
                    break
            else:
                card_best = current_card

            # 超过十次就退出
            if swipe_count > 10:
                self.utilize_erroe_num += 1
                self.config.notifier.push(title=self.config.task.command, content=f"没有合适可以蹭的卡, Swipe count is more than 10")
                logger.warning('Swipe count is more than 10')
                return

            # 一直向下滑动
            self.swipe(self.S_U_UP, interval=0.9)
            swipe_count += 1
            time.sleep(1)
        # 最好的结界卡
        logger.info('End best card is %s', card_best)

        # 进入结界
        self.screenshot()
        if not self.appear(self.I_U_ENTER_REALM):
            logger.warning('Cannot find enter realm button')
            # 可能是滑动的时候出错
            logger.warning('The best reason is that the swipe is wrong')
            return
        wait_timer = Timer(20)
        wait_timer.start()
        while 1:
            self.screenshot()
            if self.appear(self.I_U_ADD_1) or self.appear(self.I_U_ADD_2):
                logger.info('Appear enter friend realm button')
                break
            if wait_timer.reached():
                logger.warning('Appear friend realm timeout')
                return
            if self.appear_then_click(self.I_CHECK_FRIEND_REALM_2, interval=1.5):
                logger.info('Click too fast to enter the friend\'s realm pool')
                continue
            if self.appear_then_click(self.I_U_ENTER_REALM, interval=2.5):
                time.sleep(0.5)
                continue
        logger.info('Enter friend realm')

        # 切换式神的类型
        self.switch_shikigami_class(shikigami_class)
        # 判断好友的有两个位置还是一个坑位
        stop_image = None
        self.screenshot()
        if self.appear(self.I_U_ADD_1):  # 右侧第一个有（无论左侧有没有）
            stop_image = self.I_U_ADD_1
        elif self.appear(self.I_U_ADD_2) and not self.appear(self.I_U_ADD_1):  # 右侧第二个有 但是最左边的没有，这表示只留有一个坑位
            stop_image = self.I_U_ADD_2
        if not stop_image:
            # 没有坑位可能是其他人的手速太快了抢占了
            logger.warning('Cannot find stop image')
            logger.warning('Maybe other people is faster than you')
            return

        self.set_shikigami(shikigami_order, stop_image)

    def check_card_num(self, card_type: str) -> int:
        self.screenshot()
        result = self.O_CARD_NUM.ocr(self.device.image)
        logger.warning(result)
        result = result.replace('+', '').replace(card_type, '')
        logger.warning('card num is [%s]', result)
        try:
            result = int(result)
        except:
            result = 0
        logger.warning('final card num is [%s]', result)
        return result

    def back_guild(self):
        """
        回到寮的界面
        :return:
        """
        while 1:
            self.screenshot()

            if self.appear(self.I_GUILD_INFO):
                break
            if self.appear(self.I_GUILD_REALM):
                break

            if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                continue
            if self.appear_then_click(self.I_UI_BACK_BLUE, interval=1):
                continue


if __name__ == "__main__":
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.check_utilize_add()
    # t.check_card_num('勾玉', 67)
    # t.screenshot()
    # print(t.appear(t.I_BOX_EXP, threshold=0.6))
    # print(t.appear(t.I_BOX_EXP_MAX, threshold=0.6))

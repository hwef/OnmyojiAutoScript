# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import re
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
    ap_max_num = 0
    jade_max_num = 0
    first_utilize = True

    def run(self):
        con = self.config.kekkai_utilize.utilize_config
        self.ui_get_current_page()
        self.ui_goto(page_guild)

        # 进入寮结界
        self.goto_realm()
        # 育成界面去蹭卡
        self.check_utilize_add()

        # 查看满级
        self.check_max_lv(con.shikigami_class)
        # 在寮结界界面检查是否有收获 收体力或者资金
        self.check_utilize_harvest()
        # 顺带收体力盒子或者是经验盒子
        self.check_box_ap_or_exp(con.box_ap_enable, con.box_exp_enable, con.box_exp_waste)

        for i in range(1, 5):
            self.ui_get_current_page()
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
            self.utilize_erroe_num += 1
            if self.utilize_erroe_num >= 5:
                logger.warning('Utilize error more than 5 times, exit')
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
                self.back_realm()
                return
            if not self.grown_goto_utilize():
                logger.info('Utilize failed, exit')
            if self.run_utilize(con.select_friend_list, con.shikigami_class, con.shikigami_order):
                self.back_guild()
            else:
                self.back_realm()

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
                              self.I_U_TAIKO_6, self.I_U_TAIKO_5, self.I_U_FISH_4, self.I_U_TAIKO_4, self.I_U_FISH_3,
                              self.I_U_TAIKO_3])
        elif rule == UtilizeRule.TAIKO:
            return ImageGrid([self.I_U_TAIKO_6, self.I_U_TAIKO_5,
                              self.I_U_FISH_6, self.I_U_FISH_5, self.I_U_TAIKO_4, self.I_U_FISH_4, self.I_U_TAIKO_3,
                              self.I_U_FISH_3])
        else:
            logger.error('Unknown utilize rule')
            raise ValueError('Unknown utilize rule')

    @cached_property
    def select_targets(self) -> ImageGrid:
        return ImageGrid([self.I_U_FISH_6, self.I_U_TAIKO_6, self.I_U_FISH_5, self.I_U_TAIKO_5])

    @cached_property
    def order_cards(self) -> list[CardClass]:
        rule = self.config.kekkai_utilize.utilize_config.utilize_rule
        result = []
        if rule == UtilizeRule.DEFAULT:
            result = [CardClass.FISH6, CardClass.TAIKO6, CardClass.FISH5, CardClass.TAIKO5,
                      CardClass.TAIKO4, CardClass.FISH4, CardClass.TAIKO3, CardClass.FISH3]
        elif rule == UtilizeRule.FISH:
            result = [CardClass.FISH6, CardClass.FISH5,
                      CardClass.TAIKO6, CardClass.TAIKO5, CardClass.FISH4, CardClass.TAIKO4, CardClass.FISH3,
                      CardClass.TAIKO3]
        elif rule == UtilizeRule.TAIKO:
            result = [CardClass.TAIKO6, CardClass.TAIKO5,
                      CardClass.FISH6, CardClass.FISH5, CardClass.TAIKO4, CardClass.FISH4, CardClass.TAIKO3,
                      CardClass.FISH3]
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

        def _current_select_best(best_card_type=None, best_card_num=0, selected_card=False):
            """
            当前选中的最优卡处理 (自动比较并操作)
            :param best_card_type: 最优卡类型('jade'/'ap')
            :param best_card_num: 已记录的最优数值
            :param selected_card: 是否处于确认选择状态
            :return: 找到符合条件返回True，否则None
            """
            # 配置参数
            CARD_CONFIG = {
                CardClass.TAIKO6: ('jade', 76),
                CardClass.TAIKO5: ('jade', 76),
                CardClass.FISH6: ('ap', 151),
                CardClass.FISH5: ('ap', 151),
            }

            if selected_card:
                logger.info(f'开始确认最优卡 {best_card_type}卡: (要求:{best_card_num})')
            else:
                logger.info('开始搜索最优卡')

            MAX_SWIPES = 15
            matches_none = 0
            card_timer = Timer(100)
            card_timer.start()
            for swipe_count in range(MAX_SWIPES + 1):

                if card_timer.reached():
                    card_timer.reset()
                    logger.info(f'蹭卡超时，返回')
                    return None
                # 截图查找目标卡片
                self.screenshot()
                all_matches = self.select_targets.find_everyone(self.device.image)
                logger.info(f"当前识别到的卡参数: {all_matches}")

                # 无匹配时的滑动处理
                if not all_matches:
                    matches_none += 1
                    if matches_none > 3:
                        logger.info(f'连续{matches_none}次滑动未发现目标，返回')
                        return None
                    logger.info(f'第{swipe_count}次滑动未发现目标' if swipe_count else '初始状态无目标')
                    self.swipe(self.S_U_UP, interval=1)
                    self.device.click_record_clear()
                    time.sleep(2)
                    continue
                self.save_image(task_name='蹭卡截图', wait_time=0, save_flag=True)
                matches_none = 0
                # 遍历所有匹配项（已按从上到下排序）
                for target, score, (x, y, w, h) in all_matches:

                    # 转换坐标到ROI
                    target_area = (x, y, w, h)
                    self.C_SELECT_CARD.roi_front = target_area
                    self.C_SELECT_CARD.roi_back = target_area

                    # 解析卡片信息
                    card_class = target_to_card_class(target)
                    logger.info(f'发现候选卡片: {card_class} @ {target_area} 匹配度: {score}')
                    if card_class not in CARD_CONFIG:
                        logger.info(f'忽略不支持的类型: {card_class}')
                        continue

                    # 处理有效卡片
                    resource_type, max_value = CARD_CONFIG[card_class]

                    self.click(self.C_SELECT_CARD)
                    time.sleep(2)

                    resource_type, current_card_num = self.check_card_num()
                    if resource_type == 'unknown' or current_card_num == 0:
                        logger.info(f'{card_class}卡, 类型: {resource_type}, 数值: {current_card_num}, 无效卡, 重新识别下一张')
                        continue
                    logger.info(f'卡类型: {resource_type} 数值: {current_card_num} (要求: {best_card_num if selected_card else max_value})')

                    # 确认选择模式
                    if selected_card:
                        if resource_type == best_card_type and current_card_num >= best_card_num:
                            logger.info(f'确认选择{resource_type}卡: {current_card_num} ≥ {best_card_num}')
                            return True
                    # 探索记录模式
                    else:
                        if current_card_num >= max_value:
                            logger.info(f'发现完美{resource_type}卡, 确认选择: {max_value}')
                            return True

                        # 动态set卡类型 jade_max_num ap_max_num
                        record_attr = f'{resource_type}_max_num'
                        if current_card_num > getattr(self, record_attr, 0):
                            logger.info(f'更新卡记录: 卡类型: {resource_type} 数值: {current_card_num}')
                            setattr(self, record_attr, current_card_num)

                self.swipe(self.S_U_UP, interval=1)
                self.device.click_record_clear()
                time.sleep(2)
                continue
            # 循环结束后统一处理失败
            logger.warning(f'滑动结束, 返回')
            return None

        logger.hr('Start utilize')
        if self.first_utilize:
            self.swipe(self.S_U_END, interval=3)
            self.first_utilize = False
            if friend == SelectFriendList.SAME_SERVER:
                self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
                self.switch_friend_list(SelectFriendList.SAME_SERVER)
            else:
                self.switch_friend_list(SelectFriendList.SAME_SERVER)
                self.switch_friend_list(SelectFriendList.DIFFERENT_SERVER)
        else:
            self.switch_friend_list(friend)

        """智能选择最优资源卡片的主控逻辑"""
        # 预定义资源优先级配置（数值按降序排列）
        RESOURCE_PRESETS = {
            'ap': [151, 143, 134, 126, 101],  # 体力预设值
            'jade': [76, 67, 59]  # 勾玉预设值
        }
        MAX_INDEX = 99  # 表示未找到的索引值

        def reset_resource_records():
            """重置资源追踪记录"""
            self.ap_max_num = 0
            self.jade_max_num = 0
            logger.warning(f'重置体力和勾玉值!')

        def get_preset_index(resource_type):
            """区间匹配版本，找到当前值能达到的最高预设区间索引"""
            best_card_num = getattr(self, f'{resource_type}_max_num', 0)
            presets = RESOURCE_PRESETS[resource_type]

            # 遍历降序排列的预设值（从高到低）
            for index, target in enumerate(presets):
                # 只要当前值 >= 当前预设值即视为达到该区间
                if best_card_num >= target:
                    logger.info(f'✅ 【{resource_type}】当前值 {best_card_num} ≥ 预设值 {target} (第{index}档)')
                    return index

            # 所有预设值都不满足时返回特殊标记
            logger.warning(f'‼️ 卡类型: {resource_type}, 数值: {best_card_num} 不符合最低预设值')
            return MAX_INDEX

        def determine_priority_resource():
            """决策应该优先选择的资源类型"""
            ap_index = get_preset_index('ap')
            jade_index = get_preset_index('jade')
            logger.info(f'预设匹配结果: 体力档位: [{ap_index}], 勾玉档位: [{jade_index}]')

            # 双资源都未命中预设值时重置状态
            if ap_index == MAX_INDEX and jade_index == MAX_INDEX:
                logger.warning('‼️ 体力与勾玉均超过所有预设区间，触发重置机制')
                reset_resource_records()
                logger.info('已返回初始状态，重新识别')
                return None, None

            # 选择索引更靠前（数值更大）的资源类型
            if ap_index <= jade_index:
                logger.info(f'🏆 最终选择体力（档位{ap_index}），目标值: {self.ap_max_num}')
                return 'ap', RESOURCE_PRESETS['ap'][ap_index]
            else:
                logger.info(f'🏆 最终选择勾玉（档位{jade_index}），目标值: {self.jade_max_num}')
                return 'jade', RESOURCE_PRESETS['jade'][jade_index]

        while 1:
            self.screenshot()

            # 存在已记录的优选值时，选择卡
            if self.ap_max_num == 0 and self.jade_max_num == 0:
                # 获取做好的卡
                if _current_select_best():
                    logger.info('搜索发现完美卡片, 直接蹭卡')
                    break
                logger.info(f'搜索找到最好的卡片：[体力+{self.ap_max_num}] [勾玉+{self.jade_max_num}]')
                return
            else:
                res_type, target_value = determine_priority_resource()
                if not res_type:
                    continue

                logger.info(f'正在尝试确认 {res_type} 卡（目标值: {target_value}）')
                if _current_select_best(res_type, target_value, selected_card=True):
                    logger.info(f'已确认最优 {res_type} 卡')
                    break
                logger.warning('确认卡片失败!')
                reset_resource_records()
                return

        logger.info('开始执行进入结界蹭卡流程')
        # 进入结界
        self.screenshot()
        self.save_image()
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

        # 判断好友的有两个位置还是一个坑位
        stop_image = None
        self.screenshot()
        if self.appear(self.I_U_ADD_1):  # 右侧第一个有（无论左侧有没有）
            logger.info('Right side has one')
            stop_image = self.I_U_ADD_1
        elif self.appear(self.I_U_ADD_2) and not self.appear(self.I_U_ADD_1):  # 右侧第二个有 但是最左边的没有，这表示只留有一个坑位
            logger.info('Right side has two')
            stop_image = self.I_U_ADD_2
        if not stop_image:
            # 没有坑位可能是其他人的手速太快了抢占了
            logger.warning('Cannot find stop image')
            logger.warning('Maybe other people is faster than you')
            return True
        # 切换式神的类型
        self.switch_shikigami_class(shikigami_class)
        # 上式神
        self.set_shikigami(shikigami_order, stop_image)
        return True

    def check_card_num1(self) -> int:
        """优化版数值提取方法，自动过滤卡片类型标识符"""
        self.screenshot()
        # OCR识别并清理非数字字符
        raw_text = self.O_CARD_NUM.ocr(self.device.image)
        logger.info(f'OCR原始结果: {raw_text}')

        # 使用正则表达式一次性移除所有干扰字符 [+体カ力勾玉]
        cleaned = re.sub(r'[+体カ力勾玉]', '', raw_text)
        logger.info(f'清理后文本: {cleaned}')

        # 安全转换数字
        try:
            return int(cleaned)
        except ValueError:
            self.config.notifier.push(title=self.config.task.command, content=f'数值转换失败, 原始内容: {raw_text} -> 清理后: {cleaned}')
            logger.warning(f'数值转换失败，原始内容: {raw_text} -> 清理后: {cleaned}')
            return 0

    def check_card_num(self) -> tuple[str, int]:
        """优化版数值提取方法，返回卡片类型及对应数值"""
        self.screenshot()
        # OCR识别
        raw_text = self.O_CARD_NUM.ocr(self.device.image)
        logger.info(f'OCR原始结果: {raw_text}')

        # 判断卡片类型
        if any(c in raw_text for c in ['体', 'カ', '力']):
            card_type = 'ap'
        elif any(c in raw_text for c in ['勾', '玉']):
            card_type = 'jade'
        else:
            logger.warning(f'卡片类型识别失败，原始内容: {raw_text}')
            self.config.notifier.push(
                title=self.config.task.command,
                content=f'卡片类型识别失败: {raw_text}'
            )
            return 'unknown', 0  # 未知类型返回0

        # 提取纯数字部分（兼容带+号的情况，如+100）
        cleaned = re.sub(r'[^\d+]', '', raw_text)  # 保留数字和加号
        match = re.search(r'\d+', cleaned)  # 匹配连续数字

        try:
            value = int(match.group()) if match else 0
        except ValueError:
            logger.warning(f'数值转换异常，清理后文本: {cleaned}')
            value = 0

        if value <= 0:
            self.config.notifier.push(
                title=self.config.task.command,
                content=f'数值异常: {raw_text} -> 解析值: {value}'
            )
            return card_type, 0

        logger.info(f'识别成功: 卡类型: {card_type}, 数值: {value}')
        return card_type, value

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

    def back_realm(self):
        # 回到寮结界
        while 1:
            self.screenshot()
            if self.appear(self.I_REALM_SHIN):
                break
            if self.appear(self.I_SHI_DEFENSE):
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

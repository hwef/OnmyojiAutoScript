# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

from module.logger import logger

from tasks.GameUi.page import page_main, page_guild
from tasks.GameUi.game_ui import GameUi
from tasks.Component.Buy.buy import Buy
from tasks.RichMan.assets import RichManAssets
from tasks.RichMan.config import MedalRoom
from tasks.RichMan.mall.friendship_points import FriendshipPoints


class Medal(FriendshipPoints):

    def execute_medal(self, con: MedalRoom = None):
        if not con:
            con = self.config.rich_man.medal_room
        if not con.enable:
            logger.info('Medal is not enable')
            return
        self._enter_medal()

        # 黑蛋
        if con.black_daruma:
            self.buy_mall_one(buy_button=self.I_ME_BLACK,remain_number=False,  buy_check=self.I_ME_CHECK_BLACK,
                              money_ocr=self.O_MALL_RESOURCE_3, buy_money=480)
        # 蓝票
        if con.mystery_amulet:
            self.buy_mall_one(buy_button=self.I_ME_BLUE, remain_number=False, buy_check=self.I_ME_CHECK_BLUE,
                              money_ocr=self.O_MALL_RESOURCE_3, buy_money=180)
        # 体力100
        if con.ap_100:
            self.buy_mall_one(buy_button=self.I_ME_AP, remain_number=False, buy_check=self.I_ME_CHECK_AP,
                              money_ocr=self.O_MALL_RESOURCE_3, buy_money=120)

        # 两颗白蛋
        if con.white_daruma:
            self.buy_mall_more(buy_button=self.I_ME_WHITE, remain_number=False, money_ocr=self.O_MALL_RESOURCE_3,
                               buy_number=2, buy_max=2, buy_money=100)
        # 十张挑战券
        if con.challenge_pass:
            self.buy_mall_more(buy_button=self.I_ME_CHALLENGE_PASS, remain_number=False, money_ocr=self.O_MALL_RESOURCE_3,
                               buy_number=con.challenge_pass, buy_max=10, buy_money=30)
        # 红蛋
        if con.red_daruma:
            self.buy_mall_more(buy_button=self.I_ME_RED, remain_number=False,
                               money_ocr=self.O_MALL_RESOURCE_3,
                               buy_number=con.red_daruma, buy_max=99, buy_money=30)
        # 破碎的咒符
        if con.broken_amulet:
            self.buy_mall_more(buy_button=self.I_ME_BROKEN, remain_number=False,
                               money_ocr=self.O_MALL_RESOURCE_3,
                               buy_number=con.broken_amulet, buy_max=99, buy_money=20)
        self.save_image()
        # 随机御魂
        if con.random_soul:
            self.buy_one_souls(self.I_ME_SOULS, self.I_ME_CHECK_SOULS)
        self.save_image()

    def buy_one_souls(self, start_click, check_image):
        """
        购买一个物品
        :param check_image: 购买确认时候的图片
        :param start_click: 开始点击
        :return:
        """

        logger.hr(start_click.name, 3)
        self.screenshot()
        # 检查是否出现了购买按钮
        logger.info(f'before buy_button.roi_front: [{start_click.roi_front}]')
        result = start_click.match(self.device.image)
        logger.info(f'after buy_button.roi_front: [{start_click.roi_front}]')
        if not result:
            logger.warning(f'Buy button test_match result [{result}]')
            return
        if not self.appear_rgb(start_click, difference=10):
            logger.warning('Buy button is not appear')
            return False
        while 1:
            self.screenshot()

            if self.appear(check_image):
                break
            if self.appear_then_click(start_click, interval=1):
                continue
        while 1:
            self.screenshot()

            result = start_click.match_gray(self.device.image)
            if result:
                if self.appear(start_click) and not self.appear_rgb(start_click, difference=10):
                    logger.warning('Buy button end')
                    return

            if self.click(self.C_BUY_ONE, interval=2.8):
                continue

        return True


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    from tasks.RichMan.assets import RichManAssets

    c = Config('mi')
    d = Device(c)
    t = Medal(c, d)

    # t.execute_medal()

    t.buy_one_souls(RichManAssets.I_ME_SOULS, RichManAssets.I_ME_CHECK_SOULS)



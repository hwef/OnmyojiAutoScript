# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
import re

from module.logger import logger
from module.atom.image import RuleImage

from tasks.GameUi.page import page_main, page_guild
from tasks.GameUi.game_ui import GameUi
from tasks.Component.Buy.buy import Buy
from tasks.RichMan.assets import RichManAssets
from tasks.RichMan.config import GuildStore

class Guild(Buy, GameUi, RichManAssets):

    def execute_guild(self, con: GuildStore=None):

        if not con.enable:
            return
        logger.hr('Start guild', 1)
        self.ui_get_current_page()
        self.ui_goto(page_guild)
        while 1:
            self.screenshot()
            if self.appear(self.I_GUILD_CLOSE_RED):
                break
            if self.appear_then_click(self.I_GUILD_SHRINE, interval=0.8):
                continue
            if self.appear_then_click(self.I_GUILD_STORE, interval=1.1):
                continue
        logger.info('Enter guild store success')
        time.sleep(0.5)
        # 功勋礼包
        self._guild_libao()
        # 风铃
        self._guild_fl()
        # 经验手札
        self._guild_exp()
        self.save_image()
        while 1:
            self.screenshot()
            # 功勋商店 购买皮肤券 现在问题是皮肤券作为下滑判断标志,下滑过程中roi_front[1]发生了变化,
            # 导致后续识别本周剩余数量位置偏差,现在解决方案是创建一个相同属性的I_GUILD_SKIN_CHECK 来作为判断标志
            if self.appear(self.I_GUILD_SKIN_CHECK):
                time.sleep(2)
                break
            if self.swipe(self.S_GUILD_STORE, interval=1.5):
                time.sleep(2)
                continue

        # 开始购买
        if con.mystery_amulet:
            # 蓝票
            self._guild_mystery_amulet()
        if con.black_daruma_scrap:
            # 黑碎
            self._guild_black_daruma_scrap()
        if con.skin_ticket:
            # 皮肤券
            self._guild_skin_ticket(con.skin_ticket)
        # 御魂
        self._guild_yuhun()
        self.save_image()
        # 回去
        while 1:
            self.screenshot()
            if self.appear(self.I_GUILD_SHRINE):
                break
            if self.appear_then_click(self.I_GUILD_CLOSE_RED, interval=1):
                continue
            if self.appear_then_click(self.I_UI_BACK_YELLOW, interval=1):
                continue

    def _guild_mystery_amulet(self):
        # 蓝票
        logger.hr('开始购买蓝票', 3)
        self.screenshot()
        if not self.buy_check_money(self.O_GUILD_TOTAL, 240):
            return False
        result = self.I_GUILD_BLUE.match(self.device.image)
        # self.save_image(wait_time=0, image_type=True)
        if not result:
            logger.warning('未识别到蓝票')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到蓝票')
            return False
        number = self.check_remain(self.I_GUILD_BLUE)
        if number == 0:
            logger.warning('蓝票购买数量不足')
            return False

        self.buy_more(self.I_GUILD_BLUE)
        time.sleep(0.5)
        return True

    def _guild_libao(self):
        # 礼包
        logger.hr('开始购买礼包', 3)
        self.screenshot()
        result = self.I_LIAOBAO.match(self.device.image)
        if not result:
            logger.warning('未识别到礼包')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到礼包')
            return False
        number = self.check_remain(self.I_LIAOBAO)
        if number == 0:
            logger.warning('礼包购买数量不足')
            return False
        self.buy_more(self.I_LIAOBAO)
        time.sleep(0.5)
        return True

    def _guild_fl(self):
        # 风铃
        logger.hr('开始购买风铃', 3)
        self.screenshot()
        result = self.I_FL.match(self.device.image)
        if not result:
            logger.warning('未识别到风铃')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到风铃')
            return False
        number = self.check_remain(self.I_FL)
        if number == 0:
            logger.warning('风铃购买数量不足')
            return False
        self.buy_more(self.I_FL)
        time.sleep(0.5)
        self.buy_more(self.I_FL)
        time.sleep(0.5)
        return True

    def _guild_exp(self):
        # 经验御札
        logger.hr('开始购买经验御札', 3)
        self.screenshot()
        result = self.I_EXP.match(self.device.image)
        if not result:
            logger.warning('未识别到经验御札')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到经验御札')
            return False
        number = self.check_remain(self.I_EXP)
        if number == 0:
            logger.warning('经验御札购买数量不足')
            return False

        self.buy_more(self.I_EXP)
        time.sleep(0.5)
        return True

    def _guild_yuhun(self):
        # 御魂
        logger.hr('开始购买御魂', 3)
        self.screenshot()
        result = self.I_YUHUN.match(self.device.image)
        if not result:
            logger.warning('未识别到御魂')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到御魂')
            return False
        number = self.check_remain(self.I_YUHUN)
        if number == 0:
            logger.warning('御魂购买数量不足')
            return False
        self.buy_more(self.I_YUHUN)
        time.sleep(0.5)
        return True

    def _guild_black_daruma_scrap(self):
        # 黑碎
        logger.hr('开始购买黑碎', 3)
        self.screenshot()
        if not self.buy_check_money(self.O_GUILD_TOTAL, 200):
            return False
        result = self.I_GUILD_SCRAP.match(self.device.image)
        if not result:
            logger.warning('未识别到黑碎')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到黑碎')
            return False
        number = self.check_remain(self.I_GUILD_SCRAP)
        if number == 0:
            logger.warning('黑碎购买数量不足')
            return False

        self.buy_one(self.I_GUILD_SCRAP, self.I_GUILD_CHECK_SCRAP, self.I_GUILD_BUY_SCRAP)
        time.sleep(0.5)
        return True

    def _guild_skin_ticket(self, num: int = 0):
        # 皮肤券
        logger.hr('开始购买皮肤券', 3)
        if num == 0:
            logger.warning('不需要购买皮肤券')
            return False
        self.screenshot()
        if not self.buy_check_money(self.O_GUILD_TOTAL, 50):
            return False
        result = self.I_GUILD_SKIN.match(self.device.image)
        if not result:
            logger.warning('未识别到皮肤券')
            self.save_image(wait_time=0, image_type=True,push_flag=True,content='未识别到皮肤券')
            return False
        # 检查功勋商店皮肤券 本周剩余数量
        number = self.check_remain(self.I_GUILD_SKIN)
        if number == 0:
            logger.warning('皮肤券购买数量不足')
            return False

        # 购买功勋商店皮肤券
        self.buy_more(self.I_GUILD_SKIN)
        time.sleep(0.5)
        return True

    def check_remain(self, image: RuleImage) -> int:
        self.O_GUILD_REMAIN.roi[0] = image.roi_front[0] - 38
        self.O_GUILD_REMAIN.roi[1] = image.roi_front[1] + 83
        logger.info(f'Image roi {image.roi_front}')
        logger.info(f'Image roi {self.O_GUILD_REMAIN.roi}')
        self.screenshot()
        result = self.O_GUILD_REMAIN.ocr(self.device.image)
        logger.warning(result)
        result = result.replace('？', '2').replace('?', '2').replace(':', '；')
        try:
            result = re.findall(r'本周剩余数量(\d+)', result)[0]
            result = int(result)
        except:
            result = 0
        logger.info('Remain: %s' % result)
        if result == 0:
            self.save_image(wait_time=0, image_type=True,push_flag=True,content=f"{image}剩余数量为0")
        return int(result)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('DU')
    d = Device(c)
    t = Guild(c, d)

    # t._guild_skin_ticket(5)
    t.execute_guild(con=c.rich_man.guild_store)



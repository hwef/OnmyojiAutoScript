from tasks.GameUi.page import Page, page_mall
from tasks.DailyTrifles.assets import DailyTriflesAssets

# 商店签到
page_store_sign = Page(DailyTriflesAssets.I_GIFT_RECOMMEND)
page_mall.link(button=DailyTriflesAssets.I_ROOM_GIFT, destination=page_store_sign)

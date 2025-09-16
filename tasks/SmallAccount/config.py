# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import timedelta
from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase


class SmallAccountName(BaseModel):
    enable_notify: bool = Field(default=False, description='消息通知')
    enable_save_img: bool = Field(default=False, description='截图保存')
    account_name: str = Field(default='未知账号', description='name')


class SmallAccount(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    small_account_name: SmallAccountName = Field(default_factory=SmallAccountName)

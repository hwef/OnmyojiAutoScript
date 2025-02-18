# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import timedelta
from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase
from enum import Enum


class BackUpConfig(BaseModel):
    # 备份日志标志
    backup_flag: bool = Field(title='Backup Flag', default=False,  description='备份日志')


class BackUp(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    back_up_config: BackUpConfig = Field(default_factory=BackUpConfig)

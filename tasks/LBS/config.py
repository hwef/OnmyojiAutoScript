# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from tasks.Component.config_base import ConfigBase, Time
from tasks.Component.config_scheduler import Scheduler


class LBSConfig(BaseModel):
    # 限制次数
    limit_count: int = Field(default=35, description='limit_count_help')
    # 限制时间
    limit_time: Time = Field(default=Time(minute=30), description='limit_time_help')


class LBS(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    lbs_config: LBSConfig = Field(default_factory=LBSConfig)

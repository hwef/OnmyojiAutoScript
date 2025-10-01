# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import timedelta
from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase


class KirinConfig(BaseModel):
    enable: bool = Field(default=False, description='enable_help')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')


class NetherWorldConfig(BaseModel):
    enable: bool = Field(default=False, description='enable_help')
    preset_enable: bool = Field(default=False, description='preset_enable_help')
    switch_group_team: str = Field(default='-1,-1', description='switch_group_team_help')


class Hunt(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    kirin_config: KirinConfig = Field(default_factory=KirinConfig)
    nether_world_config: NetherWorldConfig = Field(default_factory=NetherWorldConfig)


from pydantic import BaseModel, Field
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase, Time


class LoopConfig(BaseModel):
    accounts_file: str = Field(default='', description='需要切换账号的文件名：比如（accounts.json）')
    # before_end: Time = Field(default=Time(0, 30, 0), description='before_end_frog_help')


class SwitchAccountLoop(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    loop_config: LoopConfig = Field(default_factory=LoopConfig)

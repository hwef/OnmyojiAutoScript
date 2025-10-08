
from pydantic import BaseModel, Field
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase, Time


class LoopConfig(BaseModel):
    accounts_file: str = Field(default='', description='需要切换账号的文件名：比如（accounts.json）')
    task_start_time: Time = Field(default=Time(6, 0, 0), description='任务开始时间')
    task_end_time: Time = Field(default=Time(23, 0, 0), description='任务结束时间')
    task_interval: Time = Field(default=Time(1, 0, 0), description='间隔时间')


class SwitchAccountLoop(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    loop_config: LoopConfig = Field(default_factory=LoopConfig)

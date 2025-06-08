# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field
from enum import Enum
from datetime import timedelta
from pydantic import BaseModel, Field
from enum import Enum
from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase, Time

class ScrollNumber(str, Enum):
    ONE = "卷一"
    TWO = "卷二"
    THREE = "卷三"
    FOUR = "卷四"
    FIVE = "卷五"
    SIX = "卷六"

class MemoryScrollsConfig(ConfigBase):
    scroll_number: ScrollNumber = Field(default=ScrollNumber.ONE, description='scroll_number_help')
    close_task: bool = Field(default=True, description='指定绘卷结束后，关闭探索和绘卷任务')

class MemoryScrolls(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    memory_scrolls_config: MemoryScrollsConfig = Field(default_factory=MemoryScrollsConfig)


# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, ValidationError, validator, Field
from tasks.Component.config_base import MultiLine

from module.logger import logger


class Team(BaseModel):
    enable: bool = Field(default=False)
    member_ip: str = Field(default="http://127.0.0.1:22288",description='成员ip地址')
    member_script_name: str = Field(default="oas1",description='成员配置脚本')


# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field


class Team(BaseModel):
    enable: bool = Field(default=False)
    member_task_stop_enable: bool = Field(default=False, description='是否中断成员当前运行的任务')
    member_ip: str = Field(default="http://127.0.0.1:22288", description='成员ip地址')
    member_script_name: str = Field(default="oas1" ,description='成员配置脚本')
    team_task_Orochi: bool = Field(default=True, description='Orochi')
    team_task_EternitySea: bool = Field(default=True, description='EternitySea')
    team_task_BondlingFairyland: bool = Field(default=True, description='BondlingFairyland')


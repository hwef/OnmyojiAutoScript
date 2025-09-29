# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from pydantic import BaseModel, Field

from tasks.Script.config_device import Device
from tasks.Script.config_error import Error
from tasks.Script.config_optimization import Optimization
from tasks.Script.config_team import Team
from tasks.Script.config_message_level import MessageLevel



class Script(BaseModel):
    device: Device = Field(default_factory=Device)
    error: Error = Field(default_factory=Error)
    message_level: MessageLevel = Field(default_factory=MessageLevel)
    optimization: Optimization = Field(default_factory=Optimization)
    team: Team = Field(default_factory=Team)
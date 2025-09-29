# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from enum import Enum
from pydantic import BaseModel, ValidationError, validator, Field
from tasks.Component.config_base import ConfigBase, Time

#
# class MessageLevelType(str, Enum):
#     ERROR = 'ERROR'     # 错误
#     INFO = 'INFO'      # 信息
#     DEBUG = 'DEBUG'     # 调试


class MessageLevel(BaseModel):
    push_notify_level: int = Field(default=3, description='消息推送级别, 数值越大级别越低, 接收到的消息就越多(Error-1、 Info-2、 Debug-3)')
    save_image_level: int = Field(default=3, description='保存截图级别, 数值越大级别越低, 保存到的截图就越多(Error-1、 Info-2、 Debug-3)')

    # push_notify_level: MessageLevelType = Field(default=MessageLevelType.DEBUG, description='消息推送级别')
    # save_image_level: MessageLevelType = Field(default=MessageLevelType.DEBUG, description='保存截图级别')


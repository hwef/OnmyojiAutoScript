# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
from module.device.device import Device
from module.logger import logger
from module.exception import RequestHumanTakeover


class DeviceManager:
    """
    全局设备，用于在Script和BaseTask类之间共享设备实例
    """
    _shared_device = None
    _device_status = False  # 设备状态，False表示未启动，True表示已启动

    @classmethod
    def get_device(cls, config=None) -> Device:
        """
        获取共享的设备实例
        Args:
            config: 配置对象，仅在首次创建设备时需要
        Returns:
            Device: 共享的设备实例
        """
        if cls._shared_device is None or not cls._device_status:
            try:
                cls._shared_device = Device(config=config)
                cls._device_status = True  # 设置设备状态为已启动
                return cls._shared_device
            except Exception as e:
                logger.exception(f'[设备] 创建设备实例时出错: {e}')
                raise
        else:
            return cls._shared_device

    @classmethod
    def get_device_status(cls) -> bool:
        """
        获取设备状态
        Returns:
            bool: 设备状态，False表示未启动，True表示已启动
        """
        return cls._device_status

    @classmethod
    def set_device_status(cls, status: bool):
        """
        设置设备状态

        Args:
            status (bool): 设备状态，False表示未启动，True表示已启动
        """
        cls._device_status = status

    @classmethod
    def reset_device(cls):
        """
        重置共享设备实例
        """
        if cls._shared_device is not None:
            # 清理资源
            try:
                cls._shared_device.release_during_wait()
                logger.debug('[设备] 设备资源释放完成')
            except Exception as e:
                logger.warning(f'[设备] 释放设备资源时出错: {e}')
            cls._shared_device = None
            cls._device_status = False
            logger.debug('[设备] 重置共享设备实例')
# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from module.device.device import Device
from module.logger import logger
from module.exception import RequestHumanTakeover

class DeviceManager:
    """
    全局设备管理器，用于在Script和BaseTask类之间共享设备实例
    """
    _shared_device = None
    
    @classmethod
    def get_device(cls, config=None) -> Device:
        """
        获取共享的设备实例
        
        Args:
            config: 配置对象，仅在首次创建设备时需要
            
        Returns:
            Device: 共享的设备实例
        """
        if cls._shared_device is None:
            if config is None:
                raise ValueError("首次创建设备实例时必须提供config参数")
            try:
                cls._shared_device = Device(config=config)
                logger.info('[设备管理器] 创建新的共享设备实例')
            except RequestHumanTakeover:
                logger.critical('[设备管理器] 设备初始化需要人工接管')
                raise
            except Exception as e:
                logger.exception(f'[设备管理器] 创建设备实例时出错: {e}')
                raise
        return cls._shared_device
    
    @classmethod
    def reset_device(cls):
        """
        重置共享设备实例
        """
        if cls._shared_device is not None:
            # 清理资源
            try:
                cls._shared_device.release_during_wait()
            except Exception as e:
                logger.warning(f'[设备管理器] 释放设备资源时出错: {e}')
            cls._shared_device = None
            logger.info('[设备管理器] 重置共享设备实例')
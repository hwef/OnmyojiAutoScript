# -*- coding: utf-8 -*-
"""
用于管理模拟器的模块，不依赖ADB连接
通过模拟器管理器直接控制模拟器的启动、关闭等操作
"""
from time import sleep

import json
import os
import subprocess
from module.logger import logger
from tasks.Script.config_device import PackageName


class EmulatorManager:
    def __init__(self, config=None):
        """
        初始化模拟器管理器
        """
        self.config = config
        self.is_client_start_by_script = False
        self.need_ask_for_close_client = False
        
        # 从配置中获取模拟器信息
        if config and hasattr(config, 'script') and hasattr(config.script, 'device'):
            self.serial = config.script.device.serial
            self.package_name = config.script.device.package_name
            self.emulator_window = config.script.device.emulator_window
        else:
            self.serial = "auto"
            self.package_name = "auto"
            self.emulator_window = "default"
            
        # 获取模拟器管理器路径
        self.manager_path = self.config.script.device.emulatorinfo_path.replace("MuMuPlayer.exe", "MuMuManager.exe")
        
        # 获取模拟器实例ID
        self.vmindex = self.get_vmindex_by_name(self.config.script.device.handle)

    def get_vmindex_by_name(self, handle):
        """
        根据模拟器名称获取索引
        """
        cmd = [self.manager_path, "info", "-v", "all"]
        result = self._execute_cmd(cmd)
        try:
            # 处理每个模拟器实例
            for index, emulator in result.items():
                # 跳过非模拟器信息的条目（如版本信息等）
                if not isinstance(emulator, dict):
                    continue

                name = emulator.get("name", f"模拟器{index}")
                adb_port = emulator.get("adb_port", None)
                if name == handle:
                    return str(index)  # 确保返回字符串类型
        except Exception as e:
            logger.error(f'根据模拟器名称获取索引时出错: {handle} 错误: {e}')

    def _execute_cmd(self, command, show_window=True):
        # logger.info(f'执行命令: {command}')
        # 隐藏CMD窗口执行命令
        startupinfo = None
        if os.name == 'nt':  # Windows系统
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            startupinfo=startupinfo,
            encoding='utf-8'  # 明确指定编码
        )
        emulators_info = json.loads(result.stdout)
        return emulators_info

    def start_emulator(self):
        """
        启动模拟器并进入游戏
        only_game (bool): 是否只启动游戏而不启动模拟器
        """
        mode = ["launch"]

        # 确保包名正确
        package = self.package_name
        if package == "auto" or package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value
            
        cmd = [self.manager_path, "control", "-v", self.vmindex, *mode, "-pkg", package]
        result = self._execute_cmd(cmd)
        if result:
            logger.info("模拟器启动成功")
        else:
            logger.error("模拟器启动失败")
            
        # 根据配置处理窗口显示
        if self.emulator_window == "min" or self.emulator_window == "最小化":
            self.hide_window()
        elif self.emulator_window == "background" or self.emulator_window == "隐藏":
            self.hide_window()
                
        return result
        
    def hide_window(self):
        """
        隐藏模拟器窗口
        """
        cmd = [self.manager_path, "control", "-v", self.vmindex, "hide_window"]
        result = self._execute_cmd(cmd)
        if result:
            logger.info("模拟器窗口已隐藏")
        else:
            logger.error("模拟器窗口隐藏失败")
        return result
        
    def show_window(self):
        """
        显示模拟器窗口
        """
        cmd = [self.manager_path, "control", "-v", self.vmindex, "show_window"]
        result = self._execute_cmd(cmd)
        if result:
            logger.info("模拟器窗口已显示")
        else:
            logger.error("模拟器窗口显示失败")
        return result
        
    def get_emulator_info(self):
        """
        获取模拟器信息
        """
        cmd = [self.manager_path, "info", "-v", self.vmindex]
        return self._execute_cmd(cmd)

    def restart_emulator(self):
        """
        重启整个模拟器
        """
        logger.info("正在重启模拟器")

        # 先关闭模拟器
        self.stop_emulator()
        sleep(5)

        # 再启动模拟器
        self.start_emulator()
        logger.info("模拟器重启完成")

    def app_start(self):
        """
        启动app
        """
        mode = ["app", "launch"]

        # 确保包名正确
        package = self.package_name
        if package == "auto" or package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value

        cmd = [self.manager_path, "control", "-v", self.vmindex, *mode, "-pkg", package]
        result = self._execute_cmd(cmd)
        if result:
            logger.info(f"{package}启动成功")
        else:
            logger.error(f"{package}启动失败 {result}")

        return result

    def stop_emulator(self):
        """
        关闭模拟器
        """
        if not self.is_emulator_running():
            logger.info("无需关闭模拟器")
        else:
            # 这里可以添加用户确认逻辑
            logger.info("正在关闭模拟器")
            self.is_client_start_by_script = False
            cmd = [self.manager_path, "control", "-v", self.vmindex, "shutdown"]
            result = self._execute_cmd(cmd)
            if result:
                logger.info("模拟器关闭成功")
            else:
                logger.error(f"模拟器关闭失败 {result}")

    def get_game_status(self):
        """
        获取游戏状态
        """
        # 确保包名正确
        package = self.package_name
        if package == "auto" or package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value
            
        cmd = [self.manager_path, "control", "-v", self.vmindex, "app", "info", "-pkg", package]
        
        result = self._execute_cmd(cmd)
        if result:
            game_state = result.get("state", None)
            return game_state
        else:
            logger.error(f"获取游戏状态失败 {result}")
            return None
            
    def app_stop(self):
        """
        关闭游戏
        """
        # 确保包名正确
        package = self.package_name
        if package == "auto" or package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value
            
        cmd = [self.manager_path, "control", "-v", self.vmindex, "app", "close", "-pkg", package]
        
        result = self._execute_cmd(cmd)
        if result:
            logger.info("游戏关闭成功")
        else:
            logger.error("游戏关闭失败")
        return result
        
    def restart_game(self):
        """
        重启游戏
        """
        logger.info("正在重启游戏")
        
        if self.is_app_running():
            self.app_stop()
            
        sleep(1)
        self.app_start()
        sleep(12)

        if self.is_app_running():
            logger.info("游戏重启完成")
        else:
            logger.error(f"游戏启动失败")

    def is_app_running(self):
        """
        检查游戏是否已启动
        """
        state = self.get_game_status()
        is_running = state == "running"
        logger.info(f"游戏运行状态: {is_running}")
        return is_running

    def is_emulator_running(self):
        """
        检查模拟器是否已启动
        """
        res = self.get_emulator_info()
        if res is None:
            return False

        is_process_started = res.get("is_process_started", False)
        logger.info(f"模拟器运行状态: {is_process_started}")
        return bool(is_process_started)


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('4399-2')
    # 创建模拟器管理器实例
    manager = EmulatorManager(config)

    # # 检查模拟器状态
    # if manager.is_emulator_running():
    #     print("模拟器正在运行")
    #     manager.get_game_status()
    #     manager.restart_game()
    #     manager.hide_window()
    #     # manager.stop_emulator()
    # else:
    #     print("模拟器未运行")
    #     # 启动模拟器
    #     manager.start_emulator()
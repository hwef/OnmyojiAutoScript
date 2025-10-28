# -*- coding: utf-8 -*-
"""
用于管理模拟器的模块，不依赖ADB连接
通过模拟器管理器直接控制模拟器的启动、关闭等操作
"""

import json
import os
import subprocess
from module.logger import logger
from tasks.Script.config_device import EmulatorWindow
from tasks.Script.config_device import PackageName
from module.server.setting import State
from deploy.process import ProcessManager
import socket


class EmulatorManager:
    def __init__(self, config=None):
        """
        初始化模拟器管理器
        """
        self.config = config
        # 获取模拟器管理器路径
        self.manager_path = self.config.script.device.emulatorinfo_path.replace("MuMuPlayer.exe", "MuMuManager.exe")

        # 获取模拟器Serial
        self.serial = config.script.device.serial
        # 获取模拟器句柄
        self.handle = self.config.script.device.handle
        # 获取模拟器实例ID
        self.vmindex = self.get_vmindex_by_name(self.handle)
        # 获取模拟器启动的app
        self.package_name = self.get_package_name()

        # 获取模拟器启动启动后窗口操作
        self.emulator_window = config.script.device.emulator_window

    def _execute_cmd(self, command):
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

    def get_emulator_info(self, vmindex):
        """
        获取模拟器信息
        """
        cmd = [self.manager_path, "info", "-v", str(vmindex)]
        return self._execute_cmd(cmd)

    def get_package_name(self):
        """
        获取正确的包名
        """
        package = self.config.script.device.package_name
        if package == PackageName.AUTO:
            package = "com.netease.onmyoji.wyzymnqsd_cps"  # 默认包名
        elif isinstance(package, PackageName):
            package = package.value
        return package

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
                if name.lower() == handle.lower():
                    # logger.info(f"模拟器名称: {name} 索引: {index}")
                    return str(index)  # 确保返回字符串类型
        except Exception as e:
            logger.error(f'根据模拟器名称获取索引时出错: {handle} 错误: {e}')

    def start_emulator(self):
        """
        启动模拟器
        MuMuPlayer.exe  可以隐藏窗口启动
        MuMuManager.exe 不能隐藏窗口启动
        """
        if self.emulator_window == EmulatorWindow.default:
            show_window = True
        else:
            show_window = False

        cmd = [self.config.script.device.emulatorinfo_path, "control", "-v", self.vmindex, "launch"]
        result = self.execute(cmd, show_window)
        if result:
            logger.info("模拟器开始启动")
        else:
            logger.error("模拟器启动失败")

    def stop_emulator(self):
        """
        关闭模拟器
        """
        if not self.is_emulator_running():
            logger.info("无需关闭模拟器")
        else:
            cmd = [self.manager_path, "control", "-v", self.vmindex, "shutdown"]
            result = self._execute_cmd(cmd)
            if result:
                logger.info("模拟器关闭成功")
                self.stop_ocr_server()
            else:
                logger.error(f"模拟器关闭失败 {result}")

    def stop_ocr_server(self):
        """
        所有模拟器关闭的情况下,关闭OCR服务
        """
        if State.deploy_config.UseOcrServer:
            cmd = [self.manager_path, "info", "-v", "all"]
            all_emulators_info = self._execute_cmd(cmd)

            for index, emulator_data in all_emulators_info.items():
                # 跳过非模拟器信息的条目
                if isinstance(emulator_data, dict):
                    is_process_started = emulator_data.get("is_process_started", False)
                    name = emulator_data.get("name", f"模拟器{index}")
                    # logger.info(f"模拟器 {name} 状态: {is_process_started}")
                    if is_process_started:
                        return
            logger.info("所有模拟器已关闭, 关闭OCR服务")
            port = State.deploy_config.OcrServerPort
            process_manager = ProcessManager()
            process_manager.kill_by_port(port=port)

    def app_start(self):
        """
        启动app
        """
        mode = ["app", "launch"]
        cmd = [self.manager_path, "control", "-v", self.vmindex, *mode, "-pkg", self.package_name]
        result = self._execute_cmd(cmd)
        if result:
            logger.info(f"{self.package_name}启动成功")
        else:
            logger.error(f"{self.package_name}启动失败 {result}")

    def app_stop(self):
        """
        关闭游戏
        """
        cmd = [self.manager_path, "control", "-v", self.vmindex, "app", "close", "-pkg", self.package_name]
        result = self._execute_cmd(cmd)
        if result:
            logger.info("游戏关闭成功")
        else:
            logger.error("游戏关闭失败")

    def get_app_status(self):
        """
        获取游戏状态
        """
        cmd = [self.manager_path, "control", "-v", self.vmindex, "app", "info", "-pkg", self.package_name]
        result = self._execute_cmd(cmd)
        if result:
            game_state = result.get("state", None)
            return game_state
        else:
            logger.error(f"获取游戏状态失败 {result}")
            return None

    def is_app_running(self):
        """
        检查游戏是否已启动
        """
        state = self.get_app_status()
        is_running = state == "running"
        # logger.info(f"游戏运行状态: {is_running}")
        return is_running

    def is_emulator_running(self):
        """
        检查模拟器是否已启动
        """
        res = self.get_emulator_info(self.vmindex)
        if res is None:
            return False
        player_state = res.get("player_state", False)
        is_start_finished = player_state == "start_finished"
        return is_start_finished
        # is_process_started = res.get("is_process_started", False)
        # logger.info(f"模拟器运行状态: {is_process_started}")
        # return bool(is_process_started)

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

    def execute(self, command, show_window=True):

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        if not show_window:
            startupinfo.wShowWindow = 0  # SW_MINIMIZE - 不显示窗口
        else:
            startupinfo.wShowWindow = 1  # SW_SHOWNORMAL - 正常显示
        # 添加CREATE_NO_WINDOW标志以防止创建新窗口
        creationflags = subprocess.CREATE_NO_WINDOW

        # logger.info(f'Execute: {command}')
        return subprocess.Popen(
            command,
            # close_fds=True, 会造成在python进程中出现木木模拟器
            startupinfo=startupinfo,
            creationflags=creationflags,
            # 重定向标准输出和标准错误以防止弹窗
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def start_ocr_server(self):

        if State.deploy_config.UseOcrServer:
            port = State.deploy_config.OcrServerPort
        else:
            logger.info("OCR 服务未启用")
            return

        def is_ocr_server_running(ocr_port):
            """检测OCR服务器是否已在运行"""
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                result = sock.connect_ex(('localhost', ocr_port))
                return result == 0

        if is_ocr_server_running(port):
            logger.info("OCR 服务已运行")
            return

        # 构建bat文件路径
        bat_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'start_OCR.bat')
        bat_file_path = os.path.abspath(bat_file_path)
        cmd = [bat_file_path]
        logger.info(f"启动OCR服务: {cmd}")
        self.execute(cmd)


if __name__ == "__main__":
    from module.config.config import Config

    config = Config('4399-2')
    # 创建模拟器管理器实例
    manager = EmulatorManager(config)
    manager.start_ocr_server()

    # # 检查模拟器状态
    # if manager.is_emulator_running():
    #     print("模拟器正在运行")
    #     manager.stop_ocr_server()
    #     # manager.get_emulator_info(1)
    #     # manager.hide_window()
    # else:
    #     print("模拟器未运行")
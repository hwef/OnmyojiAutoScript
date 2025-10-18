# This Python file uses the following encoding: utf-8
# copy from alas
import os
import re
import subprocess
import time

import adbutils
import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice

from module.base.decorator import cached_property
from module.config.config import Config
from module.config.utils import deep_iter
from module.exception import RequestHumanTakeover
from module.logger import logger

class ConnectionAttr:
    config: Config
    serial: str

    adb_binary_list = [
        './bin/adb/adb.exe',
        './toolkit/Lib/site-packages/adbutils/binaries/adb.exe',
        '/usr/bin/adb'
    ]

    def __init__(self, config):
        """
        Args:
            config (AzurLaneConfig, str): Name of the user config under ./config
        """
        logger.hr('Device', level=1)
        if isinstance(config, str):
            self.config = Config(config, task=None)
        else:
            self.config = config

        # Init adb client
        logger.attr('AdbBinary', self.adb_binary)
        logger.info(f"[ConnectionAttr] Initializing with ADB binary: {self.adb_binary}")
        # Monkey patch to custom adb
        adbutils.adb_path = lambda: self.adb_binary
        # Remove global proxies, or uiautomator2 will go through it
        count = 0
        d = dict(**os.environ)
        #----------------------------------------------------------------------------------下面的是我注释掉的
        # d.update(self.config.args)
        for _, v in deep_iter(d, depth=3):
            if not isinstance(v, dict):
                continue
            if 'oc' in v['type'] and v['value']:
                count += 1
        if count >= 3:
            for k, _ in deep_iter(d, depth=1):
                if 'proxy' in k[0].split('_')[-1].lower():
                    del os.environ[k[0]]
        else:
            su = super(self.config.__class__, self.config)
            for k, v in deep_iter(su.__dict__, depth=1):
                if not isinstance(v, str):
                    continue
                if 'eri' in k[0].split('_')[-1]:
                    print(k, v)
                    su.__setattr__(k[0], chr(8) + v)
        # Cache adb_client
        logger.info("[ConnectionAttr] Initializing adb_client")
        _ = self.adb_client

        # Parse custom serial
        # self.serial = str(self.config.Emulator_Serial)
        self.serial = str(self.config.script.device.serial)
        logger.info(f"[ConnectionAttr] Using device serial: {self.serial}")
        self.serial_check()
        self.config.DEVICE_OVER_HTTP = self.is_over_http
        logger.info(f"[ConnectionAttr] Initialization completed")

    def serial_check(self):
        """
        serial check
        """
        logger.info(f"[Serial Check] Checking serial: {self.serial}")
        # Chinese colon
        if '：' in self.serial:
            self.serial = self.serial.replace('：', ':')
            logger.warning(f'Serial {self.config.Emulator_Serial} is revised to {self.serial}')
            self.config.Emulator_Serial = self.serial
        if self.is_bluestacks4_hyperv:
            logger.info("[Serial Check] Handling BlueStacks4 Hyper-V")
            self.serial = self.find_bluestacks4_hyperv(self.serial)
        if self.is_bluestacks5_hyperv:
            logger.info("[Serial Check] Handling BlueStacks5 Hyper-V")
            self.serial = self.find_bluestacks5_hyperv(self.serial)
        if "127.0.0.1:58526" in self.serial:
            logger.warning('Serial 127.0.0.1:58526 seems to be WSA, '
                           'please use "wsa-0" or others instead')
            raise RequestHumanTakeover
        if self.is_wsa:
            logger.info("[Serial Check] Handling WSA device")
            self.serial = '127.0.0.1:58526'
            if self.config.script.device.screenshot_method != 'uiautomator2' \
                    or self.config.script.device.control_method != 'uiautomator2':
                with self.config.multi_set():
                    self.config.script.device.screenshot_method = 'uiautomator2'
                    self.config.script.device.control_method = 'uiautomator2'
        if self.is_over_http:
            logger.info("[Serial Check] Handling HTTP connection")
            if self.config.script.device.screenshot_method not in ["ADB", "uiautomator2", "aScreenCap"] \
                    or self.config.script.device.control_method not in ["ADB", "uiautomator2", "minitouch"]:
                logger.warning(
                    f'When connecting to a device over http: {self.serial} '
                    f'ScreenshotMethod can only use ["ADB", "uiautomator2", "aScreenCap"], '
                    f'ControlMethod can only use ["ADB", "uiautomator2", "minitouch"]'
                )
                raise RequestHumanTakeover
        logger.info(f"[Serial Check] Serial check completed. Final serial: {self.serial}")

    @cached_property
    def is_bluestacks4_hyperv(self):
        return "bluestacks4-hyperv" in self.serial

    @cached_property
    def is_bluestacks5_hyperv(self):
        return "bluestacks5-hyperv" in self.serial

    @cached_property
    def is_bluestacks_hyperv(self):
        return self.is_bluestacks4_hyperv or self.is_bluestacks5_hyperv

    @cached_property
    def is_wsa(self):
        return bool(re.match(r'^wsa', self.serial))

    @cached_property
    def is_mumu_family(self):
        return self.serial == '127.0.0.1:7555'

    @cached_property
    def is_emulator(self):
        return self.serial.startswith('emulator-') or self.serial.startswith('127.0.0.1:')

    @cached_property
    def is_network_device(self):
        return bool(re.match(r'\d+\.\d+\.\d+\.\d+:\d+', self.serial))

    @cached_property
    def is_over_http(self):
        return bool(re.match(r"^https?://", self.serial))

    @cached_property
    def is_chinac_phone_cloud(self):
        # Phone cloud with public ADB connection
        # Serial like xxx.xxx.xxx.xxx:301
        return bool(re.search(r":30[0-9]$", self.serial))

    @staticmethod
    def find_bluestacks4_hyperv(serial):
        """
        Find dynamic serial of BlueStacks4 Hyper-V Beta.

        Args:
            serial (str): 'bluestacks4-hyperv', 'bluestacks4-hyperv-2' for multi instance, and so on.

        Returns:
            str: 127.0.0.1:{port}
        """
        from winreg import HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

        logger.info("Use BlueStacks4 Hyper-V Beta")
        logger.info("Reading Realtime adb port")

        if serial == "bluestacks4-hyperv":
            folder_name = "Android"
        else:
            folder_name = f"Android_{serial[19:]}"

        try:
            with OpenKey(HKEY_LOCAL_MACHINE,
                         rf"SOFTWARE\BlueStacks_bgp64_hyperv\Guests\{folder_name}\Config") as key:
                port = QueryValueEx(key, "BstAdbPort")[0]
        except FileNotFoundError:
            logger.error(rf'Unable to find registry HKEY_LOCAL_MACHINE\SOFTWARE\BlueStacks_bgp64_hyperv\Guests\{folder_name}\Config')
            logger.error('Please confirm that your are using BlueStack 4 hyper-v and not regular BlueStacks 4')
            logger.error(r'Please check if there is any other emulator instances under '
                         r'registry HKEY_LOCAL_MACHINE\SOFTWARE\BlueStacks_bgp64_hyperv\Guests')
            raise RequestHumanTakeover
        logger.info(f"New adb port: {port}")
        return f"127.0.0.1:{port}"

    @staticmethod
    def find_bluestacks5_hyperv(serial):
        """
        Find dynamic serial of BlueStacks5 Hyper-V.

        Args:
            serial (str): 'bluestacks5-hyperv', 'bluestacks5-hyperv-1' for multi instance, and so on.

        Returns:
            str: 127.0.0.1:{port}
        """
        from winreg import HKEY_LOCAL_MACHINE, OpenKey, QueryValueEx

        logger.info("Use BlueStacks5 Hyper-V")
        logger.info("Reading Realtime adb port")

        if serial == "bluestacks5-hyperv":
            parameter_name = r"bst\.instance\.(Nougat64|Pie64)\.status\.adb_port"
        else:
            parameter_name = rf"bst\.instance\.(Nougat64|Pie64)_{serial[19:]}\.status.adb_port"

        try:
            with OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt") as key:
                directory = QueryValueEx(key, 'UserDefinedDir')[0]
        except FileNotFoundError:
            try:
                with OpenKey(HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt_cn") as key:
                    directory = QueryValueEx(key, 'UserDefinedDir')[0]
            except FileNotFoundError:
                logger.error('Unable to find registry HKEY_LOCAL_MACHINE\SOFTWARE\BlueStacks_nxt '
                             'or HKEY_LOCAL_MACHINE\SOFTWARE\BlueStacks_nxt_cn')
                logger.error('Please confirm that you are using BlueStacks 5 hyper-v and not regular BlueStacks 5')
                raise RequestHumanTakeover
        logger.info(f"Configuration file directory: {directory}")

        with open(os.path.join(directory, 'bluestacks.conf'), encoding='utf-8') as f:
            content = f.read()
        port = re.search(rf'{parameter_name}="(\d+)"', content)
        if port is None:
            logger.warning(f"Did not match the result: {serial}.")
            raise RequestHumanTakeover
        port = port.group(2)
        logger.info(f"Match to dynamic port: {port}")
        return f"127.0.0.1:{port}"

    @cached_property
    def adb_binary(self):
        # Try adb in deploy.yaml
        # from module.webui.setting import State
        # file = State.deploy_config.AdbExecutable
        # file = file.replace('\\', '/')
        # if os.path.exists(file):
        #     return os.path.abspath(file)
        #
        # # Try existing adb.exe
        # for file in self.adb_binary_list:
        #     if os.path.exists(file):
        #         return os.path.abspath(file)

        # Try adb in python environment - 修复路径问题
        import sys
        file = os.path.join(sys.executable, '../Lib/site-packages/adbutils/binaries/adb.exe')
        file = os.path.abspath(file).replace('\\', '/')
        if os.path.exists(file):
            logger.info(f'Using adb binary: {file}')
            return file

        # Try existing adb.exe in common paths
        for path in self.adb_binary_list:
            if os.path.exists(path):
                logger.info(f'Using adb binary: {os.path.abspath(path)}')
                return os.path.abspath(path)

        # Use adb in system PATH
        file = 'adb'
        logger.info('Using adb from system PATH')
        return file

    @cached_property
    def adb_client(self) -> AdbClient:
        host = '127.0.0.1'
        port = 5037

        # Trying to get adb port from env
        env = os.environ.get('ANDROID_ADB_SERVER_PORT', None)
        if env is not None:
            try:
                port = int(env)
                logger.info(f"[ADB Client] Using ADB port from environment: {port}")
            except ValueError:
                logger.warning(f'Invalid environ variable ANDROID_ADB_SERVER_PORT={port}, using default port')

        # Ensure ADB server is running with the correct binary
        logger.info("[ADB Client] Ensuring ADB server is running")
        try:
            self._execute_adb_command(['start-server'], timeout=10)
            time.sleep(1)
            logger.info("[ADB Client] ADB server started successfully")
        except Exception as e:
            logger.warning(f'[ADB Client] Failed to start ADB server: {e}')

        logger.attr('AdbClient', f'AdbClient({host}, {port})')
        logger.info(f"[ADB Client] Creating AdbClient instance with host={host}, port={port}")
        client = AdbClient(host, port)
        logger.info(f"[ADB Client] AdbClient instance created successfully")
        return client

    def _execute_adb_command(self, command, timeout=10, capture_output=True):
        """
        统一执行ADB命令的方法
        
        Args:
            command (list): ADB命令参数列表
            timeout (int): 超时时间
            capture_output (bool): 是否捕获输出
            
        Returns:
            subprocess.CompletedProcess: 命令执行结果
        """
        # 获取ADB二进制文件路径
        adb_path = self.adb_binary
        logger.info(f"[Execute ADB Command] ADB binary path: {adb_path}")
        # 使用隐藏窗口方式执行
        startupinfo = None
        if os.name == 'nt':  # Windows系统
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        # 构造完整命令
        if adb_path and adb_path != 'adb':
            full_command = [adb_path] + command
        else:
            full_command = ['adb'] + command

        cmd_display = ' '.join(full_command)
        logger.info(f"[Execute ADB Command] Running: {cmd_display}")
        try:
            # 执行命令
            result = subprocess.run(
                full_command,
                capture_output=capture_output,
                text=True if capture_output else False,
                timeout=timeout,
                startupinfo=startupinfo
            )
            logger.info(f"[Execute ADB Command] Command finished with return code: {result.returncode}")
            if capture_output and result.stdout:
                logger.info(f"[Execute ADB Command] Command stdout: {result.stdout}")
            if capture_output and result.stderr:
                logger.info(f"[Execute ADB Command] Command stderr: {result.stderr}")
            return result
        except subprocess.TimeoutExpired as e:
            logger.error(f"[Execute ADB Command] Command timeout: {cmd_display}")
            raise
        except Exception as e:
            logger.error(f"[Execute ADB Command] Error executing command {cmd_display}: {e}")
            raise

    @cached_property
    def adb(self) -> AdbDevice:
        logger.info(f"[ADB Device] Creating AdbDevice instance for serial: {self.serial}")
        device = AdbDevice(self.adb_client, self.serial)
        logger.info(f"[ADB Device] AdbDevice instance created successfully")
        return device

    @cached_property
    def u2(self) -> u2.Device:
        logger.info(f"[u2 Device] Creating u2.Device instance for serial: {self.serial}")
        logger.info(f"[u2 Device] Connection type: {'HTTP' if self.is_over_http else 'USB/Network'}")
        if self.is_over_http:
            # Using uiautomator2_http
            logger.info(f"[u2 Device] Connecting over HTTP: {self.serial}")
            device = u2.connect(self.serial)
        else:
            # Normal uiautomator2
            if self.serial.startswith('emulator-') or self.serial.startswith('127.0.0.1:'):
                logger.info(f"[u2 Device] Connecting via USB with serial: {self.serial}")
                device = u2.connect_usb(self.serial)
            else:
                logger.info(f"[u2 Device] Connecting via network with serial: {self.serial}")
                device = u2.connect(self.serial)

        # Stay alive
        logger.info("[u2 Device] Setting new command timeout to 604800 seconds")
        device.set_new_command_timeout(604800)

        logger.attr('u2.Device', f'Device(atx_agent_url={device._get_atx_agent_url()})')
        logger.info(f"[u2 Device] u2.Device instance created successfully")
        return device



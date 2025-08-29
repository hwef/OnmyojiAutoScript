# This Python file uses the following encoding: utf-8
# copy from alas https://github.com/LmeSzinc/AzurLaneAutoScript
from deploy.config import DeployConfig
from deploy.logger import logger
from deploy.utils import *


class ProcessManager(DeployConfig):
    @cached_property
    def process_folder(self):
        return [
            self.filepath("PythonExecutable"),
            self.root_filepath
        ]

    @cached_property
    def self_pid(self):
        return os.getpid()

    def iter_process_by_name(self, name):
        """
        Args:
            name (str): process name, such as 'alas.exe'

        Yields:
            str, str, str: executable_path, process_name, process_id
        """
        try:
            from win32com.client import GetObject
        except ModuleNotFoundError:
            logger.info('pywin32 not installed, skip')
            return False

        try:
            wmi = GetObject('winmgmts:')
            processes = wmi.InstancesOf('Win32_Process')
            for p in processes:
                executable_path = p.Properties_["ExecutablePath"].Value
                process_name = p.Properties_("Name").Value
                process_id = p.Properties_["ProcessID"].Value

                if executable_path is not None and process_name == name and process_id != self.self_pid:
                    executable_path = executable_path.replace(r'\\', '/').replace('\\', '/')
                    for folder in self.process_folder:
                        if folder in executable_path:
                            yield executable_path, process_name, process_id
        except Exception as e:
            # Possible exception
            # pywintypes.com_error: (-2147217392, 'OLE error 0x80041010', None, None)
            logger.info(str(e))
            return False

    def kill_by_name(self, name):
        """
        Args:
            name (str): Process name
        """
        logger.hr(f'Kill {name}', 1)
        for row in self.iter_process_by_name(name):
            logger.info(' '.join(map(str, row)))
            self.execute(f'taskkill /f /pid {row[2]}', allow_failure=True, output=False)

    def kill_oas_server(self):
        """
        更精确地杀死OAS服务器进程，避免影响其他Python程序
        """
        # 杀死所有运行server.py的Python进程
        killed_pids = []

        for name in ['python.exe', 'pythonw.exe']:
            for row in self.iter_process_by_name(name):
                # 检查命令行参数是否包含server.py
                try:
                    executable_path, process_name, process_id = row
                    # 获取进程的命令行参数
                    from win32com.client import GetObject
                    wmi = GetObject('winmgmts:')
                    processes = wmi.ExecQuery(f'Select * from Win32_Process where ProcessId = {process_id}')
                    for p in processes:
                        cmdline = p.CommandLine
                        if cmdline and 'server.py' in cmdline.lower() and process_id not in killed_pids:
                            logger.info(f'Killing OAS server tree: {cmdline}')
                            # 使用 /t 参数杀死进程树（包括子进程）
                            # 允许失败，因为进程可能已经结束
                            result = self.execute(f'taskkill /f /t /pid {process_id}', allow_failure=True, output=False)
                            if result:
                                logger.info(f'Successfully killed process {process_id}')
                            else:
                                # 检查进程是否还存在
                                logger.info(f'Failed to kill process {process_id}')
                            killed_pids.append(process_id)
                except Exception as e:
                    logger.info(f'Error checking process {process_id}: {e}')

    def process_kill(self):
        logger.hr(f'Kill  OAS  Server', 0)
        self.kill_oas_server()
        # self.kill_by_name("pythonw.exe")


if __name__ == '__main__':
    # ProcessManager().kill_by_name('pythonw')
    ProcessManager().process_kill()

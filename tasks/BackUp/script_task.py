# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import copy
from time import sleep

import locale
import os
import shutil
from datetime import datetime, timedelta, time
from tasks.base_task import BaseTask

from module.logger import logger, log_path, log_names
from module.exception import TaskEnd

""" 备份日志 """


class ScriptTask(BaseTask):

    def run(self):
        logger.set_file_logger(Config.config_name)
        con = self.config.back_up.back_up_config
        if con.backup_flag:
            # 根据文件创建时间移动旧文件到动态备份目录
            self.move_old_files_to_backup()
            # 递归删除空文件夹
            self.remove_empty_folders()
        self.set_next_run('BackUp', success=True, finish=True)
        raise TaskEnd('BackUp')

    def move_old_files_to_backup(self, base_path: str = log_path, days_threshold: int = 1):
        """
        递归遍历所有子文件夹，根据文件创建时间移动旧文件到动态备份目录
        :param base_path: 基础路径，包含需要检查的文件和子文件夹
        :param days_threshold: 天数阈值，默认为7天
        """

        logger.info('开始执行文件备份....')
        logger.info(f"文件路径：{self.get_real_path(base_path)}")
        backup_root = r'.\backup'
        logger.info(f"备份路径：{self.get_real_path(backup_root)}")

        # 递归遍历目录
        for root, dirs, files in os.walk(base_path):
            # 忽略隐藏文件和目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            files = [f for f in files if not f.startswith('.')]

            for file_name in files:
                if file_name.split('.')[0] in log_names or file_name == 'server.log':
                    logger.warning(f'Skip [{file_name}]')
                    continue
                file_path = os.path.join(root, file_name)
                try:
                    file_stat = os.stat(file_path)
                    # 获取文件创建时间（跨平台兼容）
                    file_time = datetime.fromtimestamp(file_stat.st_ctime)
                    # 获取文件修改时间（跨平台兼容）
                    # file_time = datetime.fromtimestamp(file_stat.st_mtime)

                    # 计算时间差
                    today = datetime.now().date()
                    time_diff = (today - file_time.date()).days

                    if time_diff >= days_threshold:
                        # 构建动态备份路径（按年-月-日组织）
                        locale.setlocale(locale.LC_TIME, 'chinese')
                        date = file_time.strftime('%Y-%m-%d %A')
                        relative_path = os.path.relpath(root, base_path)  # 保留相对路径
                        backup_path = os.path.join(backup_root, date, relative_path)
                        # 检查并创建备份目录
                        os.makedirs(backup_path, exist_ok=True)

                        backup_file_path = os.path.join(backup_path, file_name)
                        shutil.move(file_path, backup_file_path)
                        logger.info(f'Move [{file_name}] ({time_diff} days ago) to [{backup_path}]')
                        # 移动文件，避免覆盖
                        # if not os.path.exists(backup_file_path):
                        #     shutil.move(file_path, backup_file_path)
                        #     logger.info(f'Move [{file_name}] ({time_diff} days ago) to [{backup_path}]')
                        # else:
                        #     logger.warning(f'Skip [{file_name}] is exists [{backup_path}]')
                except Exception as e:
                    logger.error(f"Error processing [{file_name}]: {str(e)}")
        logger.info(f"文件备份已完成!")

    def remove_empty_folders(self, path: str = log_path):
        """
        递归删除空文件夹
        :param path: 要检查的路径
        """
        logger.info('开始删除空文件夹....')
        abs_path = os.path.abspath(path)
        for root, dirs, files in os.walk(path, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                # 排除符号链接目录和根目录
                is_symbolic_link = os.path.islink(dir_path)
                is_root_dir = os.path.samefile(dir_path, abs_path)
                is_empty = not os.listdir(dir_path)

                if not is_symbolic_link and not is_root_dir and is_empty:
                    try:
                        os.rmdir(dir_path)
                        logger.info(f"Removed empty folder: {dir_path}")
                    except OSError as e:
                        logger.warning(f"Failed to remove {dir_path}: {str(e)}")
        logger.info('删除空文件夹完成!')


    def get_real_path(self, path: str = log_path):
        """
        获取给定路径的真实路径，并检查目录是否存在。

        :param path: 相对于当前工作目录的路径
        :return: 真实路径，如果目录不存在则返回 None
        """
        try:
            # 获取当前工作目录
            current_directory = os.getcwd()

            # 构建 base_path 的完整路径
            full_path = os.path.join(current_directory, path)

            # 获取 base_path 的真实路径
            real_path = os.path.realpath(full_path)

            # 检查目录是否存在
            if os.path.exists(real_path) and os.path.isdir(real_path):
                # logger.info(f"真实目录路径: {real_path}")
                return real_path
            else:
                logger.info(f"目录 {real_path} 不存在")
                return None
        except Exception as e:
            logger.error(f"获取真实路径时发生错误: {e}")
            return None


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('test')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()

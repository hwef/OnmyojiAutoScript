# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import locale
import shutil
import zerorpc
import zmq
import msgpack
import random
import re
import cv2
import time
import os
import inflection
import asyncio
import json

from typing import Callable
from datetime import datetime, timedelta
from pathlib import Path
from cached_property import cached_property
from pydantic import BaseModel, ValidationError
from threading import Thread
from multiprocessing.queues import Queue

from module.config.utils import convert_to_underscore
from module.config.config import Config
from module.config.config_model import ConfigModel
from module.device.device import Device
from module.base.utils import load_module
from module.base.decorator import del_cached_property
from module.logger import logger, log_path, log_names
from module.exception import *


class Script:
    def __init__(self, config_name: str = 'oas') -> None:
        self.device = None
        logger.hr('Start', level=0)
        self.server = None
        self.state_queue: Queue = None
        self.gui_update_task: Callable = None  # 回调函数, gui进程注册当每次config更新任务的时候更新gui的信息
        self.config_name = config_name
        # Skip first restart
        self.is_first_task = True
        # Failure count of tasks
        # Key: str, task name, value: int, failure count
        self.failure_record = {}
        # 运行loop的线程
        self.loop_thread: Thread = None

    @cached_property
    def config(self) -> "Config":
        try:
            from module.config.config import Config
            config = Config(config_name=self.config_name)
            return config
        except RequestHumanTakeover:
            logger.critical('Request human takeover')
            exit(1)
        except Exception as e:
            logger.exception(e)
            exit(1)

    # @cached_property
    # def device(self) -> "Device":
    #     try:
    #         from module.device.device import Device
    #         device = Device(config=self.config)
    #         return device
    #     except RequestHumanTakeover:
    #         logger.critical('Request human takeover')
    #         exit(1)
    #     except Exception as e:
    #         logger.exception(e)
    #         exit(1)

    @cached_property
    def checker(self):
        """
        占位函数，在alas中是检查服务器是否正常的
        :return:
        """
        return None

    def save_error_log(self, error_message='Exception'):
        """
        Save last 60 screenshots in ./log/error/<timestamp>
        Save logs to ./log/error/<timestamp>/log.txt
        """
        from module.base.utils import save_image
        from module.handler.sensitive_info import (handle_sensitive_image,
                                                   handle_sensitive_logs)
        if self.config.script.error.save_error:
            error_path = log_path + '/error/'
            if not os.path.exists(error_path):
                os.mkdir(error_path)
            config_name = self.config.config_name.upper()
            datetime_now = datetime.now()
            now_date = datetime_now.strftime('%Y-%m-%d')
            now_time = datetime_now.strftime('%H-%M-%S')

            folder = f'{error_path}'
            image_name = f'{config_name} {now_time} ({now_date})'
            error_path_log = f'{folder}/{image_name}.log'
            error_path_image = f'{folder}/{image_name}.png'
            logger.warning(f'Saving error folder: {folder}')
            if not os.path.exists(folder):
                os.mkdir(folder)
            for data in self.device.screenshot_deque:
                image = handle_sensitive_image(data['image'])
                save_image(image, error_path_image)
            with open(logger.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                start = 0
                for index, line in enumerate(lines):
                    line = line.strip(' \r\t\n')
                    if re.match('^═{15,}$', line):
                        start = index
                lines = lines[start - 2:]
                lines = handle_sensitive_logs(lines)
            with open(error_path_log, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            logger.warn(f'asyncio push message to tg start')
            title = f'{self.config.config_name} {error_message}'
            asyncio.run(self.config.pushtg.telegram_send(title, error_path_image, error_path_log))
            logger.warn(f'asyncio push message to tg end')

    def init_server(self, port: int) -> int:
        """
        初始化zerorpc服务，返回端口号
        :return:
        """
        self.server = zerorpc.Server(self)
        try:
            self.server.bind(f'tcp://127.0.0.1:{port}')
            return port
        except zmq.error.ZMQError:
            logger.error(f"Ocr server cannot bind on port {port}")
            return None

    def run_server(self) -> None:
        """
        启动zerorpc服务
        :return:
        """
        self.server.run()

    def gui_args(self, task: str) -> str:
        """
        获取给gui显示的参数
        :return:
        """
        return self.config.gui_args(task=task)

    def gui_menu(self) -> str:
        """
        获取给gui显示的菜单
        :return:
        """
        return self.config.gui_menu

    def gui_task(self, task: str) -> str:
        """
        获取给gui显示的任务 的参数的具体值
        :return:
        """
        return self.config.model.gui_task(task=task)

    def gui_set_task(self, task: str, group: str, argument: str, value) -> bool:
        """
        设置给gui显示的任务 的参数的具体值
        :return:
        """
        # 验证参数
        task = convert_to_underscore(task)
        group = convert_to_underscore(group)
        argument = convert_to_underscore(argument)
        # pandtic验证
        if isinstance(value, str):
            if len(value) == 8:
                try:
                    value = datetime.strptime(value, '%H:%M:%S').time()
                except ValueError:
                    pass

        path = f'{task}.{group}.{argument}'
        task_object = getattr(self.config.model, task, None)
        group_object = getattr(task_object, group, None)
        argument_object = getattr(group_object, argument, None)

        if argument_object is None:
            logger.error(f'Set arg {task}.{group}.{argument}.{value} failed')
            return False

        try:
            setattr(group_object, argument, value)
            argument_object = getattr(group_object, argument, None)
            logger.info(f'Set arg {task}.{group}.{argument}.{argument_object}')
            self.config.save()  # 我是没有想到什么方法可以使得属性改变自动保存的
            return True
        except ValidationError as e:
            logger.error(e)
            return False

    @zerorpc.stream
    def gui_mirror_image(self):
        """
        获取给gui显示的镜像
        :return: cv2的对象将 numpy 数组转换为字节串。接下来MsgPack 进行序列化发送方将图像数据转换为字节串
        """
        # return msgpack.packb(cv2.imencode('.jpg', self.device.screenshot())[1].tobytes())
        img = cv2.cvtColor(self.device.screenshot(), cv2.COLOR_RGB2BGR)
        self.device.stuck_record_clear()
        ret, buffer = cv2.imencode('.jpg', img)
        yield buffer.tobytes()

    def _gui_update_tasks(self) -> None:
        """
        获取更新任务后 pending waiting 的任务 和 当前的任务的数据。打包给gui显示
        :return:
        """
        data = {}
        pending = []
        waiting = []
        task = {}
        if self.config.task is not None and self.config.task.next_run < datetime.now():
            task["name"] = self.config.task.command
            task["next_run"] = str(self.config.task.next_run)
        data["task"] = task

        for p in self.config.pending_task[1:]:
            item = {"name": p.command, "next_run": str(p.next_run)}
            pending.append(item)

        for w in self.config.waiting_task:
            item = {"name": w.command, "next_run": str(w.next_run)}
            waiting.append(item)

        data["pending"] = pending
        data["waiting"] = waiting

        if self.gui_update_task is not None:
            self.gui_update_task(data)

    def _gui_set_status(self, status: str) -> None:
        """
        设置给gui显示的状态
        :param status: 可以在gui中显示的状态 有 "Init", "Empty"(不显示), "Run"(运行中), "Error", "Free"(空闲)
        :return:
        """
        data = {"status": status}
        if self.gui_update_task is not None:
            self.gui_update_task(data)

    def gui_task_list(self) -> str:
        """
        获取给gui显示的任务列表
        :return:
        """
        result = {}
        for key, value in self.config.model.dict().items():
            if isinstance(value, str):
                continue
            if key == "restart":
                continue
            if "scheduler" not in value:
                continue

            scheduler = value["scheduler"]
            item = {"enable": scheduler["enable"],
                    "next_run": str(scheduler["next_run"])}
            key = self.config.model.type(key)
            result[key] = item
        return json.dumps(result)

    def wait_until(self, future):
        """
        Wait until a specific time.

        Args:
            future (datetime):

        Returns:
            bool: True if wait finished, False if config changed.
        """
        future = future + timedelta(seconds=1)
        self.config.start_watching()
        while 1:
            if datetime.now() > future:
                return True
            # if self.stop_event is not None:
            #     if self.stop_event.is_set():
            #         logger.info("Update event detected")
            #         logger.info(f"[{self.config_name}] exited. Reason: Update")
            #         exit(0)

            time.sleep(5)

            if self.config.should_reload():
                return False

    def countdown(self, num, action):
        """
        倒计时函数，参数为倒计时的总秒数
        """
        for i in range(num, 0, -1):
            logger.warning(f"{i} seconds to {action}")  # 动态刷新当前剩余时间
            time.sleep(1)
        logger.warning("倒计时完成！")
        logger.info(f'Wait until {self.config.next_run} for task `{self.config.command}`')

    def get_next_task(self) -> str:
        """
        获取下一个任务的名字, 大驼峰。
        :return:
        """
        while 1:
            task = self.config.get_next()
            self.config.task = task
            if self.state_queue:
                self.state_queue.put({"schedule": self.config.get_schedule_data()})

            if task.next_run > datetime.now():
                logger.info(f'Wait until {task.next_run} for task `{task.command}`')

                close_game_time = self.config.script.optimization.close_game_time
                close_emulator_time = self.config.script.optimization.close_emulator_time

                close_game_time_flag = False if close_game_time.hour == 0 and close_game_time.minute == 0 and close_game_time.second == 0 else True
                close_emulator_time_flag = False if close_emulator_time.hour == 0 and close_emulator_time.minute == 0 and close_emulator_time.second == 0 else True

                close_game_time = timedelta(hours=close_game_time.hour, minutes=close_game_time.minute,
                                            seconds=close_game_time.second)
                close_emulator_time = timedelta(hours=close_emulator_time.hour, minutes=close_emulator_time.minute,
                                                seconds=close_emulator_time.second)

                if close_emulator_time_flag and task.next_run > datetime.now() + close_emulator_time:
                    self.config.notifier.push(title='CloseMuMu',
                                              content=f'Wait `{task.command}` {str(task.next_run.time())}')
                    self.countdown(30, 'close emulator')
                    logger.info('close emulator during wait')
                    self.device.emulator_stop()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                elif close_game_time_flag and task.next_run > datetime.now() + close_game_time:
                    self.countdown(10, 'close game')
                    logger.info('close game during wait')
                    self.device.app_stop()
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
                else:
                    logger.info('Goto main page during wait')
                    self.device.release_during_wait()
                    if not self.wait_until(task.next_run):
                        del_cached_property(self, 'config')
                        continue
            break

        return task.command

    def run(self, command: str) -> bool:
        """

        :param command:  大写驼峰命名的任务名字
        :return:
        """

        if command == 'start' or command == 'goto_main':
            logger.error(f'Invalid command `{command}`')

        try:
            self.device.screenshot()
            module_name = 'script_task'
            module_path = str(Path.cwd() / 'tasks' / command / (module_name + '.py'))
            logger.info(f'module_path: {module_path}, module_name: {module_name}')
            task_module = load_module(module_name, module_path)
            task_module.ScriptTask(config=self.config, device=self.device).run()
        except TaskEnd:
            return True
        except GameNotRunningError as e:
            logger.warning(e)
            self.config.task_call('Restart')
            return True
        except GameStuckError as e:
            logger.error(e)
            self.save_error_log('Game Wait too long')
            logger.warning(f'Game stuck, {self.device.package} will be restarted in 10 seconds')
            self.config.notifier.push(title=command,
                                      content=f"<{self.config_name}> GameStuckError Wait too long ")
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GameTooManyClickError as e:
            logger.error(e)
            self.save_error_log('Game Too Many Click')
            logger.warning(f'Game Too Many Click, {self.device.package} will be restarted in 10 seconds')
            self.config.notifier.push(title=command,
                                      content=f"<{self.config_name}> Game Too Many Click")
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GameBugError as e:
            logger.warning(e)
            self.save_error_log('GameBugError')
            logger.warning('An error has occurred in Azur Lane game client, Alas is unable to handle')
            logger.warning(f'Restarting {self.device.package} to fix it')
            self.config.task_call('Restart')
            self.device.sleep(10)
            return False
        except GamePageUnknownError:
            logger.info('Game server may be under maintenance or network may be broken, check server status now')
            # 这个还不重要 留着坑填
            logger.critical('Game page unknown')
            self.save_error_log('Game page unknown')
            self.config.task_call('Restart')
            self.device.sleep(10)
            self.config.notifier.push(title=command, content=f"<{self.config_name}> GamePageUnknownError")
            # exit(1)
            return False
        except ScriptError as e:
            logger.critical(e)
            logger.critical('This is likely to be a mistake of developers, but sometimes just random issues')
            self.config.notifier.push(title=command, content=f"<{self.config_name}> ScriptError")
            exit(1)
        except RequestHumanTakeover as e:
            logger.critical(e)
            logger.critical('Request human takeover')
            self.config.notifier.push(title=command, content=f"<{self.config_name}> RequestHumanTakeover")
            exit(1)
        except Exception as e:
            logger.exception(e)
            self.save_error_log()
            self.config.notifier.push(title=command, content=f"<{self.config_name}> Exception occured")
            exit(1)

    def loop(self):
        """
        Main loop of scheduler.
        :return:
        """
        # 执行日志
        logger.set_file_logger(self.config_name)
        logger.info(f'Start scheduler loop: {self.config_name}')

        # 线程启动设置running_task is None
        self.config.model.running_task = None

        while 1:

            if self.is_first_task:
                self.device = Device(self.config)

            # 获取下一个任务
            task = self.get_next_task()

            # Skip first restart
            if self.is_first_task and task == 'Restart':
                logger.info('Skip task `Restart` at scheduler start')
                self.config.task_delay(task='Restart', success=True, server=True)
                del_cached_property(self, 'config')
                continue

            # self.config.notifier.push(title='StartMuMu', content=f'Start task `{task}`')
            self.device = Device(self.config)

            # Run
            self.device.stuck_record_clear()
            self.device.click_record_clear()

            logger.hr(f'{task} START', 0)
            logger.info(f'Scheduler: Start task `{task}`')
            success = self.run(inflection.camelize(task))
            logger.info(f'Scheduler: End task `{task}`')
            logger.hr(f'{task} END', 0)
            self.is_first_task = False

            # Check failures
            # failed = deep_get(self.failure_record, keys=task, default=0)
            failed = self.failure_record[task] if task in self.failure_record else 0
            failed = 0 if success else failed + 1
            # deep_set(self.failure_record, keys=task, value=failed)
            self.failure_record[task] = failed
            if failed >= 3:
                logger.critical(f"Task `{task}` failed 3 or more times.")
                logger.critical("Possible reason #1: You haven't used it correctly. "
                                "Please read the help text of the options.")
                logger.critical("Possible reason #2: There is a problem with this task. "
                                "Please contact developers or try to fix it yourself.")
                logger.critical('Request human takeover')
                self.config.notifier.push(title=task, content=f"<{self.config_name}> Task failed 3 or more times")
                exit(1)

            if success:
                del_cached_property(self, 'config')
                continue
            elif self.config.script.error.handle_error:
                # self.config.task_delay(success=False)
                del_cached_property(self, 'config')
                # self.checker.check_now()
                continue
            else:
                break

    def start_loop(self) -> None:
        """
        创建一个线程，运行loop
        :return:
        """
        if self.loop_thread is None:
            self.loop_thread = Thread(target=self.loop, name='Script_loop')
            self.loop_thread.start()


if __name__ == "__main__":
    script = Script("du")
    script.loop()
    # while 1:
    # script = Script("oas3")
    # device = Device("oas3")
    # device.app_start()
    # time.sleep(10)
    # logger.info('Start app')
    # device.app_stop()
    # logger.info('Stop app')
    # time.sleep(5)
    # device.emulator_stop()
    # time.sleep(5)
    # del_cached_property(script, 'device')
    # del_cached_property(script, 'config')
    # script.start_loop()
    # script.save_error_log()
    # locale.setlocale(locale.LC_TIME, 'chinese')
    # today = datetime.now()
    # date = today.strftime('%Y-%m-%d %A')
    # print(locale.windows_locale.values())  # Windows
    # print(date)
    # print(script.gui_task_list())
    # print(script.config.gui_menu)

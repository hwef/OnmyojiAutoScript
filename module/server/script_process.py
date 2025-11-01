# This Python file uses the following encoding: utf-8
# @author runhey
# 脚本进程
# github https://github.com/runhey
import multiprocessing
import queue
from asyncio import CancelledError, sleep
from enum import Enum
from module.logger import logger
from module.server.script_websocket import ScriptWSManager
from test.test_asyncgen import asyncio


class ScriptState(int, Enum):
    INACTIVE = 0
    RUNNING = 1
    WARNING = 2
    UPDATING = 3


class ScriptProcess(ScriptWSManager):

    def __init__(self, config_name: str) -> None:
        super().__init__()
        self.config_name = config_name  # config_name
        self.log_pipe_out, self.log_pipe_in = multiprocessing.Pipe(False)
        self.state_queue = multiprocessing.Queue()
        self.state: ScriptState = ScriptState.INACTIVE
        self._process = None

    async def start(self):
        self.state = ScriptState.RUNNING

        # logger.info(f'[启动] 启动脚本 {self.config_name}')
        await self.broadcast_state({"state": self.state})
        if self._process:
            logger.warning(f'Script {self.config_name} is initialized')
        if self._process and self._process.is_alive():
            logger.warning(f'Script {self.config_name} is already running and first stop it')
            self.stop()
        self._process = multiprocessing.Process(target=func,
                                                args=(self.config_name, self.state_queue, self.log_pipe_in,),
                                                name=self.config_name,
                                                daemon=True)
        self._process.start()
        # logger.info(f"进程已启动，PID: {self._process.pid}")
        # logger.info(f"进程是否存活: {self._process.is_alive()}")

    async def stop(self):
        self.state = ScriptState.INACTIVE
        # logger.info(f'[停止] 停止脚本 {self.config_name}')
        await self.broadcast_state({"state": self.state})
        if self._process is None:
            logger.warning(f'Script {self.config_name} process is removed')
            return
        if not self._process.is_alive():
            logger.warning(f'Script {self.config_name} is not running')
            return
        self._process.terminate()
        self._process = None

    async def coroutine_broadcast_state(self):
        try:
            while True:
                if self.state == ScriptState.INACTIVE:
                    await sleep(1)
                    continue
                try:
                    # 使用短超时的阻塞获取，避免频繁轮询
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, self.state_queue.get, True, 1
                    )
                    if data:
                        if 'state' in data and data['state'] == ScriptState.WARNING:
                            self.state = ScriptState.WARNING
                        await self.broadcast_state(data)

                except queue.Empty:
                    # 超时继续循环，保持响应性
                    continue
                except Exception as e:
                    logger.error(f'Error: {e}')

        except CancelledError:
            logger.warning(f'{self.config_name} state coroutine is cancelled')
            return

    async def coroutine_broadcast_log(self):
        try:
            while True:
                if self.state == ScriptState.INACTIVE:
                    await sleep(0.5)
                    continue
                try:
                    # 使用短超时的阻塞获取，避免频繁轮询
                    log = await asyncio.get_event_loop().run_in_executor(
                        None, self.log_pipe_out.recv
                    )
                    if log:
                        await self.broadcast_log(log)

                except queue.Empty:
                    # 超时继续循环，保持响应性
                    continue
                except Exception as e:
                    logger.error(f'Log Error: {e}')

        except CancelledError:
            logger.warning(f'{self.config_name} log coroutine is cancelled')
            return


def func(config: str, state_queue: multiprocessing.Queue, log_pipe_in) -> None:
    # 添加最开始的调试信息
    logger.info(f"[DEBUG] 子进程启动，配置: {config}")

    def start_log() -> None:
        try:
            from module.logger import set_file_logger, set_func_logger
            set_file_logger(name=config)
            set_func_logger(log_pipe_in.send)
        except Exception as e:
            logger.exception(f'Start log error')
            logger.error(f'Error: {e}')
            raise

    start_log()
    import time
    try:
        from script import Script
        script = Script(config_name=config)
        script.state_queue = state_queue
        logger.hr(f'Script `{config}` is running', 0)
        script.start_loop()
    except SystemExit as e:
        logger.info(f'Script {config} process exit')
        logger.error(f'Error: {e}')
        state_queue.put({"state": ScriptState.WARNING})
        time.sleep(0.1)
        exit(-1)
    except Exception as e:
        logger.exception(f'Run script {config} error')
        logger.error(f'Error: {e}')
        raise


if __name__ == '__main__':
    p = ScriptProcess('oas1')
    p.start()
    from time import sleep

    sleep(10)
    logger.info(p._process.exitcode)

# This Python file uses the following encoding: utf-8

import time
from time import sleep

from datetime import datetime, timedelta
from functools import wraps


def timer(function):
    """
    装饰器 打印函数时间时间
    """
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()

        result = function(*args, **kwargs)
        t1 = time.time()
        print('%s: %s s' % (function.__name__, str(round(t1 - t0, 10))))
        return result

    return function_timer


def future_time(string):
    """
    Args:
        string (str): Such as 14:59.

    Returns:
        datetime.datetime: Time with given hour, minute in the future.
    """
    hour, minute = [int(x) for x in string.split(':')]
    future = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    future = future + timedelta(days=1) if future < datetime.now() else future
    return future


def past_time(string):
    """
    Args:
        string (str): Such as 14:59.

    Returns:
        datetime.datetime: Time with given hour, minute in the past.
    """
    hour, minute = [int(x) for x in string.split(':')]
    past = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = past - timedelta(days=1) if past > datetime.now() else past
    return past


def future_time_range(string):
    """
    Args:
        string (str): Such as 23:30-06:30.

    Returns:
        tuple(datetime.datetime): (time start, time end).
    """
    start, end = [future_time(s) for s in string.split('-')]
    if start > end:
        start = start - timedelta(days=1)
    return start, end


def time_range_active(time_range):
    """
    Args:
        time_range(tuple(datetime.datetime)): (time start, time end).

    Returns:
        bool:
    """
    return time_range[0] < datetime.now() < time_range[1]


class Timer:
    def __init__(self, limit, count=0):
        """
        Args:
            limit (int, float): Timer limit
            count (int): Timer reach confirm count. Default to 0.
                When using a structure like this, must set a count.
                Otherwise it goes wrong, if screenshot time cost greater than limit.

                if self.appear(MAIN_CHECK):
                    if confirm_timer.reached():
                        pass
                else:
                    confirm_timer.reset()

                Also, It's a good idea to set `count`, to make alas run more stable on slow computers.
                Expected speed is 0.35 second / screenshot.
        """
        self.limit = limit
        self.count = count
        self._current = 0
        self._reach_count = count

    def start(self):
        """
        启动计时器。

        如果计时器尚未启动，则初始化当前时间和到达次数。

        Returns:
            self: 返回自身实例，支持链式调用
        """
        if not self.started():
            self._current = time.time()
            self._reach_count = 0

        return self

    def started(self):
        """
        检查计时器是否已启动。

        Returns:
            bool: 如果计时器已启动返回True，否则返回False
        """
        return bool(self._current)

    def current(self):
        """
        获取当前经过的时间。

        Returns:
            float: 自计时器启动以来经过的时间（秒），如果未启动则返回0.0
        """
        if self.started():
            return time.time() - self._current
        else:
            return 0.

    def reached(self):
        """
        检查计时器是否达到限制条件。

        计时器达到限制需要同时满足两个条件：
        1. 经过的时间超过设定的limit
        2. 到达次数超过设定的count

        Returns:
            bool: 如果达到限制条件返回True，否则返回False
        """
        self._reach_count += 1
        return time.time() - self._current > self.limit and self._reach_count > self.count

    def reset(self):
        """
        重置计时器。

        将当前时间设为现在，并将到达次数清零。

        Returns:
            self: 返回自身实例，支持链式调用
        """
        self._current = time.time()
        self._reach_count = 0
        return self

    def clear(self):
        """
        清除计时器状态。

        将当前时间设为0，并将到达次数设为预设的count值。

        Returns:
            self: 返回自身实例，支持链式调用
        """
        self._current = 0
        self._reach_count = self.count
        return self

    def reached_and_reset(self):
        """
        检查计时器是否达到限制并重置。

        如果计时器达到限制条件，则重置计时器并返回True；
        否则返回False。

        Returns:
            bool: 如果达到限制条件返回True，否则返回False
        """
        if self.reached():
            self.reset()
            return True
        else:
            return False

    def wait(self):
        """
        等待直到计时器达到限制时间。

        计算剩余等待时间，如果还有剩余时间则进行睡眠等待。
        """
        diff = self._current + self.limit - time.time()
        if diff > 0:
            time.sleep(diff)

    def show(self):
        """
        显示计时器信息。

        使用logger输出计时器的字符串表示。
        """
        from module.logger import logger
        logger.info(str(self))


    def __str__(self):
        return f'Timer(limit={round(self.current(), 3)}/{self.limit}, count={self._reach_count}/{self.count})'

    __repr__ = __str__


if __name__ == '__main__':
    t = Timer(1.2)
    sleep(1.2)
    t.reset()
    while not t.reached():
        print(t.current())
        sleep(5)

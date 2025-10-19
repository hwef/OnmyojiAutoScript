# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import numpy as np

from module.base.decorator import cached_property
from module.logger import logger

class RuleClick:

    def __init__(self, roi_front: tuple, roi_back: tuple, name: str = None) -> None:
        """
        初始化
        :param roi_front:
        :param roi_back:
        """
        self.roi_front = roi_front
        self.roi_back = roi_back
        if name:
            self.name = name
        else:
            self.name = 'click'

    def coord(self) -> tuple:
        """
        获取坐标, 从roi_front使用正态分布获取坐标
        :return:
        """
        x, y, w, h = self.roi_front
        # 使用正态分布生成坐标，均值为中心点
        # 这样可以确保大约99.7%的点落在区域内
        center_x = x + w // 2
        center_y = y + h // 2
        # 标准差 σ（控制分布范围，通常取 ROI 宽度/高度的 1/4 ~ 1/2）
        sigma_x = w / 4  # 可调整，比如 w/3, w/2
        sigma_y = h / 4  # 可调整，比如 h/3, h/2

        # 生成正态分布的随机坐标（但限制在 ROI 范围内）
        while True:
            # 生成正态分布的 x 和 y（均值=中心点，标准差=σ）
            rand_x = int(np.random.normal(center_x, sigma_x))
            rand_y = int(np.random.normal(center_y, sigma_y))

            # 确保坐标在 ROI 范围内 [x, x+w] × [y, y+h]
            if x <= rand_x <= x + w and y <= rand_y <= y + h:
                return rand_x, rand_y

    def coord_more(self) -> tuple:
        """
        从roi_back随机获取坐标
        :return:
        """
        x, y, w, h = self.roi_back
        x = np.random.randint(x, x + w)
        y = np.random.randint(y, y + h)
        return x, y

    @property
    def center(self) -> tuple:
        """
        返回roi_front的中心坐标
        :return:
        """
        x, y, w, h = self.roi_front
        return x + w // 2, y + h // 2

    def move(self, x: int, y: int) -> None:
        """
        移动roi_front, 需要限幅x是0-1280, y是0-720
        :param x:
        :param y:
        :return:
        """
        x, y, w, h = self.roi_front
        x += x
        y += y
        if x <= 0 :
            x = 0
        elif x >= 1280:
            x = 1280

        if y <= 0 :
            y = 0
        elif y >= 720:
            y = 720

        self.roi_front = x, y, w, h

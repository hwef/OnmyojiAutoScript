# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import numpy as np

from module.atom.image import RuleImage



class ImageGrid:

    def __init__(self, images: list[RuleImage]):
        self.images = images


    def find_anyone(self, img: np.array) -> RuleImage or None:
        """
        在这些图片中找到其中一个
        :param img:
        :return: 如果没有找到返回None
        """
        for image in self.images:
            if image.match(img):
                return image
        return None

    def find_everyone(self, img: np.array) -> RuleImage or None:
        """
        自下而上在这些图片中找到第一个，匹配的
        :param img:
        :return: 如果没有找到返回None
        """
        all_matches = []
        for image in self.images:
            # 获取当前image的匹配结果（已经是过滤后的列表）
            current_matches = image.match_all_any(img, threshold=0.8, nms_threshold=0.3)
            # 将当前结果合并到总列表
            all_matches.extend(current_matches)

        # 去掉得分部分，只保留坐标和尺寸 (x, y, w, h)
        final_results = [(x, y, w, h) for (score, x, y, w, h) in all_matches]

        return final_results

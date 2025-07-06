# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time
import cv2
import numpy as np

from ppocronnx.predict_system import BoxedResult
from enum import Enum


from module.base.decorator import cached_property
from module.base.utils import area_pad, crop, float2str
from module.ocr.ppocr import TextSystem
from module.ocr.models import OCR_MODEL
from module.exception import ScriptError
from module.logger import logger



def enlarge_canvas(image):
    """
    copy from https://github.com/LmeSzinc/StarRailCopilot
    Enlarge image into a square fill with black background. In the structure of PaddleOCR,
    image with w:h=1:1 is the best while 3:1 rectangles takes three times as long.
    Also enlarge into the integer multiple of 32 cause PaddleOCR will downscale images to 1/32.
    """
    height, width = image.shape[:2]
    length = int(max(width, height) // 32 * 32 + 32)
    border = (0, length - height, 0, length - width)
    if sum(border) > 0:
        image = cv2.copyMakeBorder(image, *border, borderType=cv2.BORDER_CONSTANT, value=(0, 0, 0))
    return image


class OcrMode(Enum):
    FULL = 1  # str: "Full"
    SINGLE = 2  # str: "Single"
    DIGIT = 3  # str: "Digit"
    DIGITCOUNTER = 4  # str: "DigitCounter"
    DURATION = 5  # str: "Duration"
    QUANTITY = 6  # str: "Quantity"

class OcrMethod(Enum):
    DEFAULT = 1  # str: "Default"

class BaseCor:

    lang: str = "ch"
    score: float = 0.6  # 阈值默认为0.5

    name: str = "ocr"
    mode: OcrMode = OcrMode.FULL
    method: OcrMethod = OcrMethod.DEFAULT  # 占位符
    roi: list = []  # [x, y, width, height]
    area: list = []  # [x, y, width, height]
    keyword: str = ""  # 默认为空


    def __init__(self,
                 name: str,
                 mode: str,
                 method: str,
                 roi: tuple,
                 area: tuple,
                 keyword: str) -> None:
        """
        初始化OCR基础类
        参数:
            name: OCR名称
            mode: OCR模式(FULL/SINGLE/DIGIT等)
            method: OCR方法
            roi: 检测区域(x,y,w,h)
            area: 实际区域(x,y,w,h)
            keyword: 关键词
        """
        if not name or not isinstance(name, str):
            raise ValueError("OCR名称不能为空且必须为字符串")
        if not mode:
            raise ValueError("OCR模式不能为空")
        if not roi or len(roi) != 4:
            raise ValueError("ROI区域必须为4元素元组(x,y,w,h)")
        if not area or len(area) != 4:
            raise ValueError("实际区域必须为4元素元组(x,y,w,h)")

        self.name = name.upper()
        if isinstance(mode, str):
            self.mode = OcrMode[mode.upper()]
        elif isinstance(mode, OcrMode):
            self.mode = mode
        else:
            raise ValueError("OCR模式必须为字符串或OcrMode枚举")

        if isinstance(method, str):
            self.method = OcrMethod[method.upper()]
        elif isinstance(method, OcrMethod):
            self.method = method
        else:
            raise ValueError("OCR方法必须为字符串或OcrMethod枚举")

        self.roi: list = list(roi)
        self.area: list = list(area)
        self.keyword = keyword if keyword else ""

    @cached_property
    def model(self):
        """
        获取当前语言的OCR模型
        返回:
            TextSystem或ONNXPaddleOcr实例
        """
        try:
            model = OCR_MODEL._get_model(self.lang)
            if not model:
                raise ValueError(f"无法获取{self.lang}语言的OCR模型")
            return model
        except Exception as e:
            logger.error(f"获取OCR模型失败: {str(e)}")
            raise

    def pre_process(self, image):
        """
        重写
        :param image:
        :return:
        """
        return image

    def after_process(self, result):
        """
        重写
        :param result:
        :return:
        """
        return result

    @classmethod
    def crop(cls, image: np.array, roi: tuple) -> np.array:
        """
        截取图片
        :param roi:
        :param image:
        :return:
        """
        x, y, w, h = roi
        return image[y:y + h, x:x + w]

    def ocr_item(self, image):
        """
        这个函数区别于ocr_single_line，这个函数不对图片进行裁剪，是什么就是什么的
        :param image:
        :return:
        """
        # pre process
        start_time = time.time()
        image = self.pre_process(image)
        # ocr
        result, score = self.model.ocr_single_line(image)
        if score < self.score:
            result = ""
        # after proces
        result = self.after_process(result)
        # logger.info("ocr result score: %s%s" % (result,score))
        logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                    text=f'[{result}]')
        return result

    def ocr_single_line(self, image):
        """
        单行OCR识别(仅支持横向文本)
        参数:
            image: 输入图像(numpy数组)
        返回:
            识别结果字符串
        异常:
            ValueError: 当输入图像无效时抛出
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("输入图像不能为空且必须为numpy数组")

        start_time = time.time()
        try:
            # 预处理
            image = self.crop(image, self.roi)
            if image.size == 0:
                raise ValueError("裁剪后的图像为空")
                
            image = self.pre_process(image)
            
            # OCR识别
            result, score = self.model.ocr_single_line(image)
            if score < self.score:
                result = ""
                
            # 后处理
            result = self.after_process(result)
            
            logger.attr(
                name=f'{self.name} {float2str(time.time() - start_time)}s',
                text=f'识别结果: [{result}] 置信度: {score:.2f}'
            )
            return result
        except Exception as e:
            logger.error(f'{self.name} OCR识别失败: {str(e)}')
            raise

    def detect_and_ocr(self, image) -> list[BoxedResult]:
        """
        多行OCR识别(支持检测和识别)
        参数:
            image: 输入图像(numpy数组)
        返回:
            识别结果列表[BoxedResult]
        异常:
            ValueError: 当输入图像无效时抛出
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("输入图像不能为空且必须为numpy数组")

        start_time = time.time()
        try:
            # 预处理
            image = self.crop(image, self.roi)
            if image.size == 0:
                raise ValueError("裁剪后的图像为空")
                
            image = self.pre_process(image)
            image = enlarge_canvas(image)

            # OCR识别
            boxed_results: list[BoxedResult] = self.model.detect_and_ocr(image)
            if not boxed_results:
                logger.info(f"{self.name} 未检测到任何文本")
                return []

            # 后处理
            results = []
            for result in boxed_results:
                if result.score < self.score:
                    continue
                result.ocr_text = self.after_process(result.ocr_text)
                results.append(result)

            logger.attr(
                name=f'{self.name} {float2str(time.time() - start_time)}s',
                text=f'检测到{len(results)}个文本区域'
            )
            return results
        except Exception as e:
            logger.error(f'{self.name} 多行OCR识别失败: {str(e)}')
            raise

    def match(self, result: str, included: bool=False) -> bool:
        """
        使用ocr获取结果后和keyword进行匹配
        :param result:
        :param included:  ocr结果和keyword是否包含关系, 要么是包含关系，要么是相等关系
        :return:
        """
        if included:
            return self.keyword in result
        else:
            return self.keyword == result

    def filter(self, boxed_results: list[BoxedResult], keyword: str=None) -> list or None:
        """
        使用ocr获取结果后和keyword进行匹配. 返回匹配的index list
        :param keyword: 如果不指定默认适用对象的keyword
        :param boxed_results:
        :return:
        """
        # 首先先将所有的ocr的str顺序拼接起来, 然后再进行匹配
        result = None
        strings = [boxed_result.ocr_text for boxed_result in boxed_results]
        concatenated_string = "".join(strings)
        if keyword is None:
            keyword = self.keyword
        if keyword in concatenated_string:
            result = [index for index, word in enumerate(strings) if keyword in word]
        else:
            result = None

        if result is not None:
            # logger.info("Filter result: %s" % result)
            return result

        # 如果适用顺序拼接还是没有匹配到，那可能是竖排的，使用单个字节的keyword进行匹配
        indices = []
        # 对于keyword中的每一个字符，都要在strings中进行匹配
        # 如果这个字符在strings中的某一个string中，那么就记录这个string的index
        max_index = len(strings) - 1
        for index, char in enumerate(keyword):
            for i, string in enumerate(strings):
                if char not in string:
                    continue
                if i <= max_index:
                    indices.append(i)
                    break
        if indices:
            # 剔除掉重复的index
            indices = list(set(indices))
            return indices
        else:
            return None

    def detect_text(self, image) -> str:
        """
        识别图片中的文字， 会按照顺序拼接起来
        :param image:
        :return:
        """
        # pre process
        start_time = time.time()
        image = self.crop(image, self.roi)
        image = self.pre_process(image)
        image = enlarge_canvas(image)
        # ocr
        boxed_results: list[BoxedResult] = self.model.detect_and_ocr(image)
        results = ''
        # after proces
        for result in boxed_results:
            # logger.info("ocr result score: %s" % result.score)
            if result.score < self.score:
                continue
            results += result.ocr_text
        # logger.info("ocr result score: %s" % score)
        logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                    text=f'[{results}]')
        return results


# def test():
#     # strings = ["探", "索"]
#     # keyword = "探索"
#     # strings是截图ocr的结果，keyword是要匹配的关键字
#     strings = ['123', '456', '789', '101112', '131415', '456']
#     keyword = '123456'
#
#     indices = []
#     # 对于keyword中的每一个字符，都要在strings中进行匹配
#     # 如果这个字符在strings中的某一个string中，那么就记录这个string的index
#     max_index = len(strings) - 1
#     for index, char in enumerate(keyword):
#         for i, string in enumerate(strings):
#             if char not in string:
#                 continue
#             if i <= max_index:
#                 indices.append(i)
#                 break
#     if indices:
#         # 剔除掉重复的index
#         indices = list(set(indices))
#         return indices
#     else:
#         return None
# print(test())
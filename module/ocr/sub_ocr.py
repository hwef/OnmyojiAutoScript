# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import cv2
import re
import cn2an
import numpy as np
from datetime import timedelta

from module.ocr.ppocr import TextSystem
from module.exception import ScriptError
from module.base.utils import area_pad, crop, float2str
from module.ocr.base_ocr import BaseCor, OcrMode, OcrMethod
from module.ocr.utils import merge_area
from module.logger import logger


class Full(BaseCor):
    """
    这个类适用于大ROI范围的文本识别。可以支持多条文本识别， 默认不支持竖方向的文本识别
    """
    def after_process(self, result):
        return result

    def ocr_full(self, image, keyword: str=None) -> tuple:
        """
        全图OCR识别并过滤结果
        参数:
            image: 输入图像(numpy数组)
            keyword: 要匹配的关键词(默认为self.keyword)
        返回:
            匹配区域的坐标(x,y,w,h), 未匹配时返回(0,0,0,0)
        异常:
            ValueError: 当输入图像无效时抛出
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("输入图像不能为空且必须为numpy数组")
            
        keyword = keyword if keyword is not None else self.keyword
        if not keyword:
            logger.warning(f"{self.name} 未设置关键词,将返回第一个检测区域")

        try:
            boxed_results = self.detect_and_ocr(image)
            if not boxed_results:
                logger.info(f"{self.name} 未检测到任何文本")
                return 0, 0, 0, 0

            index_list = self.filter(boxed_results, keyword)
            if not index_list:
                logger.info(f"{self.name} 未找到匹配关键词'{keyword}'的区域")
                return 0, 0, 0, 0

            # 处理匹配区域
            if len(index_list) > 1:
                logger.info(f"{self.name} 找到{len(index_list)}个匹配区域")
                area_list = [(
                    boxed_results[index].box[0, 0],  # x
                    boxed_results[index].box[0, 1],  # y
                    boxed_results[index].box[1, 0] - boxed_results[index].box[0, 0],  # width
                    boxed_results[index].box[2, 1] - boxed_results[index].box[0, 1],  # height
                ) for index in index_list]
                area = merge_area(area_list)
                self.area = (
                    area[0] + self.roi[0], 
                    area[1] + self.roi[1], 
                    area[2], 
                    area[3]
                )
            else:
                box = boxed_results[index_list[0]].box
                self.area = (
                    box[0, 0] + self.roi[0],
                    box[0, 1] + self.roi[1],
                    box[1, 0] - box[0, 0],
                    box[2, 1] - box[0, 1]
                )

            logger.info(f"{self.name} 匹配区域坐标: {self.area}")
            return self.area
        except Exception as e:
            logger.error(f"{self.name} 全图OCR识别失败: {str(e)}")
            raise

class Single(BaseCor):
    """
    这个类使用于单行文本识别（所识别的ROI不会动）
    """
    def after_process(self, result):
        return result

    def ocr_single(self, image, return_score=False) -> str:
        """
        单行OCR识别(支持横向和纵向文本)
        参数:
            image: 输入图像(numpy数组)
        返回:
            识别结果字符串, 未识别到返回空字符串
        异常:
            ValueError: 当输入图像无效或ROI未设置时抛出
        """
        if image is None or not isinstance(image, np.ndarray):
            raise ValueError("输入图像不能为空且必须为numpy数组")
        if not self.roi:
            raise ValueError("ROI区域未设置")

        try:
            # 首先尝试横向识别
            ocr_result = self.ocr_single_line(image)
            if isinstance(ocr_result, tuple):
                result, score = ocr_result
            else:
                result = ocr_result
                score = 1.0  # 默认置信度
                
            if return_score:
                return result, score
            else:
                return result

            # # 横向识别失败,尝试纵向识别
            # logger.info(f"{self.name} 尝试纵向文本识别")
            # boxed_results = self.detect_and_ocr(image)
            # if not boxed_results:
            #     logger.info(f"{self.name} ROI区域内未检测到文本")
            #     return ""
            #
            # # 返回置信度最高的结果
            # best_result = max(boxed_results, key=lambda x: x.score)
            # if best_result.score > self.score:
            #     return best_result.ocr_text
            #
            # logger.info(f"{self.name} 文本置信度过低: {best_result.score:.2f}")
            # return ""
        except Exception as e:
            logger.error(f"{self.name} 单行OCR识别失败: {str(e)}")
            raise

class Digit(Single):

    def after_process(self, result):
        """
        数字OCR结果后处理
        参数:
            result: 原始识别结果
        返回:
            处理后的数字(int)
        """
        if isinstance(result, int):
            return result
        elif not isinstance(result, str):
            raise ValueError("输入结果必须为字符串")

        # 常见字符替换
        replace_rules = {
            'I': '1', 'D': '0', 'S': '5',
            'B': '8', '？': '2', '?': '2',
            'd': '6', 'o': '0', 'O': '0'
        }
        
        for old, new in replace_rules.items():
            result = result.replace(old, new)

        # 只保留数字字符
        digits = [char for char in result if char.isdigit()]
        result_str = ''.join(digits)
        
        # 转换为整数
        try:
            result_int = int(result_str) if result_str else 0
        except ValueError:
            logger.warning(f"{self.name} 数字转换失败: {result_str}")
            result_int = 0

        # 记录修正情况
        if result_str and str(result_int) != result_str:
            logger.warning(f'{self.name} 数字修正: "{result_str}" -> "{result_int}"')

        return result_int

    def ocr_digit(self, image, return_score=False) -> int:
        """
        数字OCR识别
        参数:
            image: 输入图像(numpy数组)
        返回:
            识别到的数字, 识别失败返回0
        异常:
            ValueError: 当输入图像无效时抛出
        """
        try:
            if return_score:
                result, score = self.ocr_single(image, return_score)
                processed_result = self.after_process(result)
                return processed_result, score
            else:
                result = self.ocr_single(image)
                processed_result = self.after_process(result)
                return processed_result
        except Exception as e:
            logger.error(f"{self.name} 数字OCR识别失败: {str(e)}")
            return 0

class DigitCounter(Single):
    def after_process(self, result):
        """
        计数器OCR结果后处理
        参数:
            result: 原始识别结果
        返回:
            处理后的计数器字符串
        """
       # 直接返回数值类型数据
        if isinstance(result ,int):
            return result
        elif not isinstance(result, str):
            raise ValueError("输入结果必须为字符串")
        # 常见字符替换
        replace_rules = {
            'I': '1', 'D': '0', 'S': '5',
            'B': '8', '？': '2', '?': '2',
            'd': '6', 'l': '1', ' ': ''
        }
        
        for old, new in replace_rules.items():
            result = result.replace(old, new)

        # 只保留数字和斜杠
        valid_chars = [char for char in result if char.isdigit() or char == '/']
        return ''.join(valid_chars)

    @classmethod
    def ocr_str_digit_counter(cls, result: str) -> tuple[int, int, int]:
        """
        解析计数器字符串
        参数:
            result: 格式为"当前值/总值"的字符串
        返回:
            元组(当前值, 剩余值, 总值)
        异常:
            ValueError: 当输入格式无效时抛出
        """
        if not result:
            return 0, 0, 0

        match = re.search(r'(\d+)/(\d+)', result)
        if not match:
            logger.warning(f"{cls.name} 无效的计数器格式: {result}")
            return 0, 0, 0

        try:
            current = int(match.group(1))
            total = int(match.group(2))
            
            if current > total:
                logger.warning(f"{cls.name} 当前值{current}大于总值{total}")
            
            return current, total - current, total
        except (ValueError, IndexError) as e:
            logger.error(f"{cls.name} 计数器解析失败: {str(e)}")
            return 0, 0, 0

    def ocr_digit_counter(self, image) -> tuple[int, int, int]:
        """
        计数器OCR识别
        参数:
            image: 输入图像(numpy数组)
        返回:
            元组(当前值, 剩余值, 总值)
        异常:
            ValueError: 当输入图像无效时抛出
        """
        try:
            result = self.ocr_single(image)
            if not result:
                logger.info(f"{self.name} 未识别到计数器")
                return 0, 0, 0
                
            return self.ocr_str_digit_counter(result)
        except Exception as e:
            logger.error(f"{self.name} 计数器OCR识别失败: {str(e)}")
            return 0, 0, 0

class Duration(Single):
    def after_process(self, result):
        """
        持续时间OCR结果后处理
        参数:
            result: 原始识别结果
        返回:
            标准化后的时间字符串
        """
        # 直接返回数值类型数据
        if isinstance(result ,int):
            return result
        elif not isinstance(result, str):
            raise ValueError("输入结果必须为字符串")
        # 常见字符替换
        replace_rules = {
            'I': '1', 'D': '0', 'S': '5',
            'o': '0', 'l': '1', 'O': '0',
            'B': '8', '：': ':', ' ': '',
            '.': ':', ';': ':', ',': ':'
        }
        
        for old, new in replace_rules.items():
            result = result.replace(old, new)

        # 确保最终格式为HH:MM:SS
        parts = result.split(':')
        if len(parts) == 2:
            result = f"{parts[0]}:{parts[1]}:00"
        elif len(parts) > 3:
            result = ":".join(parts[:3])

        return result

    @staticmethod
    def parse_time(string) -> timedelta:
        """
        解析时间字符串为timedelta
        参数:
            string: 时间字符串(HH:MM:SS格式)
        返回:
            datetime.timedelta对象
        异常:
            ValueError: 当时间格式无效时抛出
        """
        if not string:
            return timedelta(0)

        match = re.search(r'(\d{1,2}):?(\d{2}):?(\d{2})', string)
        if not match:
            logger.warning(f"无效的时间格式: {string}")
            return timedelta(0)

        try:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            
            # 验证时间单位范围
            if minutes >= 60 or seconds >= 60:
                raise ValueError("分钟或秒数超过范围")
                
            return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (ValueError, IndexError) as e:
            logger.error(f"时间解析失败: {str(e)}")
            return timedelta(0)

    def ocr_duration(self, image) -> timedelta:
        """
        持续时间OCR识别
        参数:
            image: 输入图像(numpy数组)
        返回:
            datetime.timedelta对象
        异常:
            ValueError: 当输入图像无效时抛出
        """
        try:
            result = self.ocr_single(image)
            if not result:
                logger.info(f"{self.name} 未识别到持续时间")
                return timedelta(0)
                
            return self.parse_time(result)
        except Exception as e:
            logger.error(f"{self.name} 持续时间OCR识别失败: {str(e)}")
            return timedelta(0)

class Quantity(BaseCor):
    """
    专门用于识别超级多的数量，不支持多个区域的识别
    可支持负数
    比如：”6.33亿“ ”1.2万“ “53万/100” -> 530,000
    """
    def after_process(self, result):
        """
        数量OCR结果后处理(支持中文数字单位)
        参数:
            result: 原始识别结果
        返回:
            处理后的数量值(int)
        异常:
            ValueError: 当输入结果无效时抛出
        """
        
        # 直接返回数值类型数据
        if isinstance(result ,int):
            return result
        elif not isinstance(result, str):
            raise ValueError("输入结果必须为字符串")
        # 常见字符替换
        replace_rules = {
            'I': '1', 'D': '0', 'S': '5',
            'B': '8', '？': '2', '?': '2',
            'd': '6', 'o': '0', 'O': '0',
            ' ': '', ',': '', '，': ''
        }
        
        for old, new in replace_rules.items():
            result = result.replace(old, new)

        # 处理分数形式(如"100/200"取分子)
        if '/' in result:
            result = result.split('/')[0]

        # 只保留数字、小数点和中文单位
        valid_chars = [char for char in result 
                      if char.isdigit() or char == '.' or char in ['万', '亿', '千']]
        result = ''.join(valid_chars)

        try:
            # 转换中文数字为阿拉伯数字
            if '万' in result or '亿' in result or '千' in result:
                quantity = cn2an.cn2an(result, 'smart')
            else:
                quantity = float(result) if '.' in result else int(result)
                
            return int(quantity)
        except Exception as e:
            logger.error(f"{self.name} 数量转换失败: {result} ({str(e)})")
            return 0

    def ocr_quantity(self, image) -> int:
        """
        数量OCR识别
        参数:
            image: 输入图像(numpy数组)
        返回:
            识别到的数量值
        异常:
            ValueError: 当输入图像无效时抛出
        """
        try:
            boxed_results = self.detect_and_ocr(image)
            if not boxed_results:
                logger.info(f"{self.name} 未检测到数量文本")
                return 0

            # 更新检测区域
            box = boxed_results[0].box
            self.area = (
                box[0, 0] + self.roi[0],
                box[0, 1] + self.roi[1],
                box[1, 0] - box[0, 0],
                box[2, 1] - box[0, 1]
            )

            # 获取并处理识别结果
            text = boxed_results[0].ocr_text
            quantity = self.after_process(text)
            
            logger.info(f"{self.name} 识别到数量: {quantity}")
            return quantity
        except Exception as e:
            logger.error(f"{self.name} 数量OCR识别失败: {str(e)}")
            return 0



if __name__ == '__main__':
    import cv2
    image = cv2.imread(r'E:\Project\OnmyojiAutoScript-assets\jade.png')
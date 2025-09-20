import sys
import os
# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from module.base.decorator import cached_property
from module.ocr.ppocr import TextSystem
from module.ocr.onnxocr.onnx_paddleocr import ONNXPaddleOcr
from module.logger import logger


class OcrModel:
    def __init__(self):
        self._model_type = 'ppocr'  # 默认使用ppocr模型
        self._onnx_params = {}  # ONNX模型参数
        self._model_cache = {}  # 模型缓存
        
    @cached_property
    def ch(self):
        """获取中文OCR模型"""
        return self._get_model('ch')
        
    def _get_model(self, lang: str):
        """
        获取指定语言的OCR模型
        参数:
            lang: 语言代码(ch/en等)
        返回:
            OCR模型实例
        """
        self._model_cache[lang] = ONNXPaddleOcr(**self._onnx_params)
        # if lang not in self._model_cache:
        #     if self._model_type == 'onnx':
        #         logger.info(f'初始化ONNX OCR模型({lang})')
        #         self._model_cache[lang] = ONNXPaddleOcr(**self._onnx_params)
        #     else:
        #         logger.info(f'初始化PPOCR模型({lang})')
        #         self._model_cache[lang] = TextSystem()
        return self._model_cache[lang]
    
    def switch_to_onnx(self, **kwargs):
        """
        切换到ONNX模型
        参数:
            **kwargs: ONNX模型参数
        """
        self._model_type = 'onnx'
        self._onnx_params = kwargs
        self._model_cache.clear()  # 清空模型缓存
        logger.info('已切换至ONNX OCR模型')
        
    def switch_to_ppocr(self):
        """
        切换回PPOCR模型
        """
        self._model_type = 'ppocr'
        self._onnx_params = {}
        self._model_cache.clear()  # 清空模型缓存
        logger.info('已切换回PPOCR模型')


OCR_MODEL = OcrModel()


if __name__ == "__main__":
    model = OCR_MODEL.ch
    import cv2
    import time
    
    # 尝试导入memory_profiler，如果失败则使用普通函数
    try:
        from memory_profiler import profile
        memory_profiling = True
    except ImportError:
        memory_profiling = False
        def profile(func):
            return func
    
    image = cv2.imread(r"H:\game\yys\OnmyojiAutoScript-easy-install\OnmyojiAutoScript-easy-install\module\ocr\1234.png")

    # 引入ocr会导致非常巨大的内存开销
    @profile
    def test_memory():
        for i in range(2):
            start_time = time.time()
            result = model.detect_and_ocr(image)
            print(result)
            end_time = time.time()
            print(f'耗时：{end_time-start_time}')

    test_memory()
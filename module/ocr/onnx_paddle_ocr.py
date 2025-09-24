import base64
import numpy as np
import onnxocr.onnx_paddleocr as onnxocr
import pickle
from typing import List


class BoxedResult(object):
    box: List[int]
    text_img: np.ndarray
    ocr_text: str
    score: float
    after_box: List[int]

    def __init__(self, box, text_img, ocr_text, score):
        self.box = box
        self.text_img = text_img
        self.ocr_text = ocr_text
        self.score = score

    def __str__(self):
        return 'BoxedResult[%s, %s]' % (self.ocr_text, self.score)

    def __repr__(self):
        return self.__str__()

    def to_dict(self):
        """Convert BoxedResult to a serializable dictionary"""
        return {
            'box': self.box.tolist(),
            'text_img': base64.b64encode(pickle.dumps(self.text_img)).decode(
                'utf-8') if self.text_img is not None else None,
            'ocr_text': self.ocr_text,
            'score': self.score
        }

    @classmethod
    def from_dict(cls, data):
        """Create BoxedResult from a dictionary"""
        text_img = None
        if data['text_img'] is not None:
            text_img = pickle.loads(base64.b64decode(data['text_img'].encode('utf-8')))

        return cls(
            box=np.array(data['box']),
            text_img=text_img,
            ocr_text=data['ocr_text'],
            score=data['score']
        )


class ONNXPaddleOcr(onnxocr.ONNXPaddleOcr):
    # use_gpu=False：是否使用GPU进行计算，False表示使用CPU
    # gpu_mem=500：分配给GPU的内存大小（MB）
    # gpu_id=0：使用的GPU设备ID（当有多个GPU时）
    # use_tensorrt=False：是否使用NVIDIA TensorRT优化推理
    # precision="fp32"：计算精度，可选"fp32"(单精度)、"fp16"(半精度)等
    # drop_score=0.5：OCR识别结果的置信度阈值，低于此值的结果会被过滤掉
    # use_angle_cls=True：是否使用文字方向分类器（处理竖排文字等）
    # cpu_threads=10：CPU推理时使用的线程数
    # benchmark=False：是否启用性能基准测试模式
    # use_onnx=True：是否使用ONNX格式的模型文件
    def __init__(self,
                 use_gpu=False,
                 gpu_mem=500,
                 gpu_id=0,
                 use_tensorrt=False,
                 precision="fp32",
                 drop_score=0.5,
                 use_angle_cls=True,
                 cpu_threads=10,
                 benchmark=False,
                 use_onnx=True
                 ):
        # 基于当前文件位置构建绝对路径
        # 获取项目根目录
        # project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 构建模型目录路径
        # det_model_dir = os.path.join(project_root, "toolkit", "Lib", "site-packages", "onnxocr", "models", "ppocrv4", "det", "det.onnx")  # 检测模型
        # rec_model_dir = os.path.join(project_root, "toolkit", "Lib", "site-packages", "onnxocr", "models", "ppocrv4", "rec", "rec.onnx")  # 识别模型
        # cls_model_dir = os.path.join(project_root, "toolkit", "Lib", "site-packages", "onnxocr", "models", "ppocrv4", "cls", "cls.onnx")  # 分类模型
        # print(f'det_model_dir: {det_model_dir}')
        # print(f'det_model_dir: {os.path.abspath(det_model_dir)}')

        super().__init__(
            use_gpu=use_gpu,
            gpu_mem=gpu_mem,
            gpu_id=gpu_id,
            use_tensorrt=use_tensorrt,
            precision=precision,
            drop_score=drop_score,
            use_angle_cls=use_angle_cls,
            cpu_threads=cpu_threads,
            benchmark=benchmark,
            use_onnx=use_onnx
            # det_model_dir=os.path.abspath(det_model_dir),
            # rec_model_dir=os.path.abspath(rec_model_dir),
            # cls_model_dir=os.path.abspath(cls_model_dir)
            # det_model_dir="D:/OnmyojiAutoScript/ljxun/toolkit/Lib/site-packages/onnxocr/models/ppocrv4/det/det.onnx",
            # rec_model_dir="D:/OnmyojiAutoScript/ljxun/toolkit/Lib/site-packages/onnxocr/models/ppocrv4/rec/rec.onnx",
            # cls_model_dir="D:/OnmyojiAutoScript/ljxun/toolkit/Lib/site-packages/onnxocr/models/ppocrv4/cls/cls.onnx"
        )

    def detect_and_ocr(self, img: np.ndarray, drop_score=None):
        """
         Detect text boxes and recognize text from the image.
        :param img: Input image in RGB format.
        :param drop_score: Input image in RGB format.
        :return: List of BoxedResult containing detected boxes, cropped images, recognized text, and scores.
        """
        rec_res = self.ocr(img, det=True, rec=True, cls=True)
        if not rec_res:
            return []
        rec_res = rec_res[0]
        res = []

        if drop_score is None:
            drop_score = self.drop_score

        for box, rec_result in rec_res:
            text, score = rec_result
            if score >= drop_score:
                # 确保box保持为numpy数组格式，支持box[0, 0]这样的索引
                if not isinstance(box, np.ndarray):
                    box = np.array(box)
                res.append(BoxedResult(box, img, text, score))
        return res

    def ocr_lines(self, img_list: List[np.ndarray]):
        tmp_img_list = []
        for img in img_list:
            img_height, img_width = img.shape[0:2]
            if img_height * 1.0 / img_width >= 1.5:
                img = np.rot90(img)
            tmp_img_list.append(img)

        rec_res = self.text_recognizer(tmp_img_list)
        return rec_res

    def ocr_single_line(self, img):
        res = self.ocr_lines([img])
        if res:
            return res[0]
        return None

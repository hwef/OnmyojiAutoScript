import os
import cv2
import copy
import time
import numpy as np
from module.logger import logger
from . import predict_det
from . import predict_cls
from . import predict_rec
from .utils import get_rotate_crop_image, get_minarea_rect_crop


class BoxedResult:
    """
    用于存储OCR结果的数据结构
    """
    def __init__(self, box, box_score, ocr_text, score, position=None):
        """
        初始化BoxedResult
        :param box: 文本框的四个顶点坐标，形状为[4, 2]
        :param box_score: 文本框的置信度
        :param ocr_text: 识别的文本
        :param score: 文本识别的置信度
        :param position: 文本框的位置，形式为[x_min, y_min, x_max, y_max]
        """
        self.box = box
        self.box_score = box_score
        self.ocr_text = ocr_text
        self.score = score
        self.position = position


class TextSystem(object):
    _instance = None
    _initialized = False

    def __new__(cls, args=None):
        if cls._instance is None:
            cls._instance = super(TextSystem, cls).__new__(cls)
        return cls._instance

    def __init__(self, args=None):
        # 如果已经初始化过，检查args是否与现有实例的args一致
        if TextSystem._initialized:
            if args is not None and hasattr(self, 'args') and self.args is not None:
                # 如果参数一致，则不再重新初始化
                if self.args == args:
                    return
                else:
                    logger.info("检测到不同的参数配置，重新初始化TextSystem")
            else:
                return
        
        # 只有在未初始化或参数不一致时，且args不为None时才初始化
        if args is not None:
            logger.info("正在初始化TextSystem(单例模式)")
            start_time = time.time()
            
            # 初始化文本检测器
            self.text_detector = predict_det.TextDetector(args)
            
            # 检查是否有rec模型目录
            self.enable_rec = hasattr(args, 'rec_model_dir') and args.rec_model_dir is not None
            if self.enable_rec:
                self.text_recognizer = predict_rec.TextRecognizer(args)
            else:
                logger.warning("未提供识别模型目录，文本识别功能将被禁用")
            
            # 初始化方向分类器
            self.use_angle_cls = args.use_angle_cls
            if self.use_angle_cls:
                self.text_classifier = predict_cls.TextClassifier(args)
            
            # 设置其他参数
            self.drop_score = args.drop_score
            self.args = args
            self.crop_image_res_index = 0
            
            total_init_time = time.time() - start_time
            logger.info(f"TextSystem初始化完成，总耗时{total_init_time:.3f}秒")
            
            # 标记为已初始化
            TextSystem._initialized = True

    def draw_crop_rec_res(self, output_dir, img_crop_list, rec_res):
        os.makedirs(output_dir, exist_ok=True)
        bbox_num = len(img_crop_list)
        for bno in range(bbox_num):
            cv2.imwrite(
                os.path.join(
                    output_dir, f"mg_crop_{bno+self.crop_image_res_index}.jpg"
                ),
                img_crop_list[bno],
            )

        self.crop_image_res_index += bbox_num

    def __call__(self, img, cls=True):
        start_time = time.time()
        
        # 保存原始图像副本
        ori_im = img.copy()
        
        # 文字检测
        dt_boxes = self.text_detector(img)
        
        if dt_boxes is None:
            return None, None
            
        if len(dt_boxes) == 0:
            return dt_boxes, []

        # 对文本框进行排序
        dt_boxes = sorted_boxes(dt_boxes)

        # 图片裁剪
        img_crop_list = []
        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            
            if self.args.det_box_type == "quad":
                img_crop = get_rotate_crop_image(ori_im, tmp_box)
            else:
                img_crop = get_minarea_rect_crop(ori_im, tmp_box)
                
            img_crop_list.append(img_crop)

        # 方向分类
        if self.use_angle_cls and cls:
            img_crop_list, angle_list = self.text_classifier(img_crop_list)

        # 图像识别
        if not self.enable_rec:
            return dt_boxes, []
            
        rec_res = self.text_recognizer(img_crop_list)

        # 过滤低置信度结果
        filter_boxes, filter_rec_res = [], []
        text_results = []  # 存储所有文本区域的结果
        
        # 存储所有识别结果，包括框、文本和置信度
        all_results = []
        for i, (box, rec_result) in enumerate(zip(dt_boxes, rec_res)):
            text, score = rec_result
            # result_info = f"区域{i+1}: '{text}'(置信度：{score:.4f})"
            # text_results.append(result_info)
            
            if score >= self.drop_score:
                # 计算文本框的位置 [x_min, y_min, x_max, y_max]
                x_min, y_min = np.min(box, axis=0)
                x_max, y_max = np.max(box, axis=0)
                position = [x_min, y_min, x_max, y_max]
                
                all_results.append(BoxedResult(box, 1.0, text, score, position))
        
        # 应用NMS处理，处理重叠文本框
        if len(all_results) > 1:
            # 按照识别置信度排序
            all_results = sorted(all_results, key=lambda x: x.score, reverse=True)
            
            # NMS处理
            keep_indices = []
            for i in range(len(all_results)):
                keep = True
                for j in keep_indices:
                    # 计算IoU
                    iou = calculate_iou(all_results[i].box, all_results[j].box)
                    # 如果IoU大于阈值，则丢弃当前框
                    if iou > 0.7:  # 设置IoU阈值为0.7
                        keep = False
                        logger.info(f"检测到重叠文本框: '{all_results[i].ocr_text}'与'{all_results[j].ocr_text}'，IoU={iou:.2f}，保留置信度更高的结果")
                        break
                if keep:
                    keep_indices.append(i)
            
            # 保留通过NMS的结果
            filtered_results = [all_results[i] for i in keep_indices]
            
            # 更新过滤后的结果
            filter_boxes = [result.box for result in filtered_results]
            filter_rec_res = [(result.ocr_text, result.score) for result in filtered_results]
        else:
            # 如果只有一个结果，直接使用
            filter_boxes = [result.box for result in all_results]
            filter_rec_res = [(result.ocr_text, result.score) for result in all_results]
        
        # # 记录最后一个结果的信息
        # if filter_rec_res:
        #     result_info = f"最终识别结果: '{filter_rec_res[-1][0]}'(置信度：{filter_rec_res[-1][1]:.4f})"
        #     logger.info(result_info)
        # else:
        #     logger.info("没有识别到有效文本")

        # 返回过滤后的结果
        return filter_boxes, filter_rec_res


def calculate_iou(box1, box2):
    """
    计算两个文本框的IoU (交并比)
    args:
        box1, box2: 文本框坐标，形状为[4, 2]
    return:
        iou: 交并比值
    """
    # 计算每个框的最小外接矩形
    x1_min, y1_min = np.min(box1, axis=0)
    x1_max, y1_max = np.max(box1, axis=0)
    x2_min, y2_min = np.min(box2, axis=0)
    x2_max, y2_max = np.max(box2, axis=0)
    
    # 计算交集区域
    inter_x1 = max(x1_min, x2_min)
    inter_y1 = max(y1_min, y2_min)
    inter_x2 = min(x1_max, x2_max)
    inter_y2 = min(y1_max, y2_max)
    
    # 如果没有交集，返回0
    if inter_x1 >= inter_x2 or inter_y1 >= inter_y2:
        return 0.0
    
    # 计算交集面积
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    
    # 计算两个框的面积
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    
    # 计算并集面积
    union_area = area1 + area2 - inter_area
    
    # 计算IoU
    iou = inter_area / union_area if union_area > 0 else 0.0
    
    return iou

def sorted_boxes(dt_boxes):
    """
    Sort text boxes in order from top to bottom, left to right
    args:
        dt_boxes(array):detected text boxes with shape [4, 2]
    return:
        sorted boxes(array) with shape [4, 2]
    """
    num_boxes = dt_boxes.shape[0]
    sorted_boxes = sorted(dt_boxes, key=lambda x: (x[0][1], x[0][0]))
    _boxes = list(sorted_boxes)

    for i in range(num_boxes - 1):
        for j in range(i, -1, -1):
            if abs(_boxes[j + 1][0][1] - _boxes[j][0][1]) < 10 and (
                _boxes[j + 1][0][0] < _boxes[j][0][0]
            ):
                tmp = _boxes[j]
                _boxes[j] = _boxes[j + 1]
                _boxes[j + 1] = tmp
            else:
                break
    return _boxes


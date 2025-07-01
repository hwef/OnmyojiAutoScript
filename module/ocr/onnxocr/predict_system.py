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
    def __init__(self, args):
        logger.info("正在初始化TextSystem")
        start_time = time.time()
        
        # 初始化文本检测器
        logger.info("正在初始化文本检测器")
        det_start_time = time.time()
        self.text_detector = predict_det.TextDetector(args)
        det_init_time = time.time() - det_start_time
        logger.info(f"文本检测器初始化完成，耗时{det_init_time:.3f}秒")
        
        # 检查是否有rec模型目录
        self.enable_rec = hasattr(args, 'rec_model_dir') and args.rec_model_dir is not None
        if self.enable_rec:
            logger.info(f"正在初始化文本识别器，模型目录：{args.rec_model_dir}")
            rec_start_time = time.time()
            self.text_recognizer = predict_rec.TextRecognizer(args)
            rec_init_time = time.time() - rec_start_time
            logger.info(f"文本识别器初始化完成，耗时{rec_init_time:.3f}秒")
        else:
            logger.warning("未提供识别模型目录，文本识别功能将被禁用")
        
        # 初始化方向分类器
        self.use_angle_cls = args.use_angle_cls
        if self.use_angle_cls:
            logger.info("正在初始化文本方向分类器")
            cls_start_time = time.time()
            self.text_classifier = predict_cls.TextClassifier(args)
            cls_init_time = time.time() - cls_start_time
            logger.info(f"文本方向分类器初始化完成，耗时{cls_init_time:.3f}秒")
        else:
            logger.info("文本方向分类器已禁用（use_angle_cls=False）")
            
        # 设置其他参数
        self.drop_score = args.drop_score
        logger.info(f"设置置信度阈值为{self.drop_score}")
        
        self.args = args
        self.crop_image_res_index = 0
        
        total_init_time = time.time() - start_time
        logger.info(f"TextSystem初始化完成，总耗时{total_init_time:.3f}秒")

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
        logger.info("开始执行TextSystem的__call__方法")
        
        # 记录图像信息
        if hasattr(img, 'shape'):
            logger.info(f"输入图像尺寸: {img.shape}")
        
        # 保存原始图像副本
        ori_im = img.copy()
        
        # 文字检测
        logger.info("开始文字检测")
        det_start_time = time.time()
        dt_boxes = self.text_detector(img)
        det_time = time.time() - det_start_time
        logger.info(f"文字检测完成，耗时{det_time:.3f}秒")

        if dt_boxes is None:
            logger.info("未检测到文本框（dt_boxes为None）")
            return None, None
            
        if len(dt_boxes) == 0:
            logger.info("未检测到文本框（空列表）")
            return dt_boxes, []

        # 对文本框进行排序
        logger.info(f"对{len(dt_boxes)}个检测到的文本框进行排序")
        dt_boxes = sorted_boxes(dt_boxes)

        # 图片裁剪
        logger.info("开始裁剪文本区域")
        img_crop_list = []
        for bno in range(len(dt_boxes)):
            tmp_box = copy.deepcopy(dt_boxes[bno])
            
            # 记录裁剪区域信息
            if hasattr(tmp_box, 'shape') and tmp_box.shape[0] >= 1:
                x_min, y_min = np.min(tmp_box, axis=0)
                x_max, y_max = np.max(tmp_box, axis=0)
                logger.info(f"裁剪第{bno+1}个区域，位置：[{x_min:.1f}, {y_min:.1f}, {x_max:.1f}, {y_max:.1f}]")
            
            # 根据检测框类型选择裁剪方法
            if self.args.det_box_type == "quad":
                img_crop = get_rotate_crop_image(ori_im, tmp_box)
                logger.info(f"第{bno+1}个区域使用旋转裁剪方法")
            else:
                img_crop = get_minarea_rect_crop(ori_im, tmp_box)
                logger.info(f"第{bno+1}个区域使用最小矩形裁剪方法")
                
            img_crop_list.append(img_crop)
            
            # 记录裁剪后的图像尺寸
            if hasattr(img_crop, 'shape'):
                logger.info(f"第{bno+1}个裁剪图像尺寸: {img_crop.shape}")

        # 方向分类
        if self.use_angle_cls and cls:
            logger.info("开始文本方向分类")
            cls_start_time = time.time()
            img_crop_list, angle_list = self.text_classifier(img_crop_list)
            cls_time = time.time() - cls_start_time
            logger.info(f"方向分类完成，耗时{cls_time:.3f}秒")
            
            # 记录分类结果
            rotated_count = sum(1 for angle in angle_list if angle == 1)
            logger.info(f"共{len(angle_list)}个文本区域，其中{rotated_count}个需要旋转")
        else:
            if not cls:
                logger.info("跳过文本方向分类（cls=False）")
            elif not self.use_angle_cls:
                logger.info("跳过文本方向分类（use_angle_cls=False）")

        # 图像识别
        if self.enable_rec:
            logger.info(f"开始识别{len(img_crop_list)}个文本区域")
            rec_start_time = time.time()
            rec_res = self.text_recognizer(img_crop_list)
            rec_time = time.time() - rec_start_time
            logger.info(f"文本识别完成，耗时{rec_time:.3f}秒")
        else:
            logger.warning("文本识别功能已禁用，返回空识别结果")
            return dt_boxes, []

        # 保存裁剪结果
        if self.args.save_crop_res:
            logger.info(f"正在保存裁剪结果到目录：{self.args.crop_res_save_dir}")
            self.draw_crop_rec_res(self.args.crop_res_save_dir, img_crop_list, rec_res)
            
        # 过滤低置信度结果
        logger.info(f"使用置信度阈值{self.drop_score}过滤结果")
        filter_boxes, filter_rec_res = [], []
        filtered_count = 0
        
        for i, (box, rec_result) in enumerate(zip(dt_boxes, rec_res)):
            text, score = rec_result
            if score >= self.drop_score:
                filter_boxes.append(box)
                filter_rec_res.append(rec_result)
                logger.info(f"第{i+1}个区域：'{text}'（置信度：{score:.4f}）- 已接受")
            else:
                filtered_count += 1
                logger.info(f"第{i+1}个区域：'{text}'（置信度：{score:.4f}）- 已过滤")
        
        logger.info(f"共{len(rec_res)}个结果中过滤掉{filtered_count}个")
        
        total_time = time.time() - start_time
        logger.info(f"TextSystem __call__方法完成，耗时{total_time:.3f}秒，共{len(filter_boxes)}个有效文本区域")
        return filter_boxes, filter_rec_res


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
import time
import numpy as np

from module.logger import logger
from .predict_system import TextSystem
from .utils import infer_args as init_args
from .utils import str2bool, draw_ocr
import argparse
import sys


class ONNXPaddleOcr(TextSystem):
    def __init__(self, **kwargs):
        logger.info("正在初始化ONNX PaddleOCR系统")
        start_time = time.time()
        
        # 默认参数
        parser = init_args()
        inference_args_dict = {}
        for action in parser._actions:
            inference_args_dict[action.dest] = action.default
        params = argparse.Namespace(**inference_args_dict)

        # 设置识别模型的图像形状
        # params.rec_image_shape = "3, 32, 320"
        params.rec_image_shape = "3, 48, 320"
        logger.info(f"设置识别模型图像形状为：{params.rec_image_shape}")

        # 记录传入的参数
        logger.info(f"初始化参数：{kwargs}")
        
        # 根据传入的参数覆盖更新默认参数
        params.__dict__.update(**kwargs)

        # 检查rec_model_dir是否为None
        self.enable_rec = params.rec_model_dir is not None
        if not self.enable_rec:
            logger.warning("未提供识别模型目录，文本识别功能将被禁用")
        else:
            logger.info(f"识别模型目录：{params.rec_model_dir}")
            
        # 记录检测模型目录
        if params.det_model_dir:
            logger.info(f"检测模型目录：{params.det_model_dir}")
        else:
            logger.warning("未提供检测模型目录")
            
        # 记录分类模型目录
        if params.cls_model_dir:
            logger.info(f"分类模型目录：{params.cls_model_dir}")
        else:
            logger.info("未提供分类模型目录")

        # 初始化模型
        logger.info("调用父类初始化")
        super().__init__(params)
        
        init_time = time.time() - start_time
        logger.info(f"ONNX PaddleOCR初始化完成，耗时{init_time:.3f}秒")

    def ocr(self, img, det=True, rec=True, cls=True):
        start_time = time.time()
        logger.info(f"Starting OCR process with det={det}, rec={rec}, cls={cls}")
        
        # 记录图像信息
        if hasattr(img, 'shape'):
            logger.info(f"Input image shape: {img.shape}")
        elif isinstance(img, list) and len(img) > 0 and hasattr(img[0], 'shape'):
            logger.info(f"Input is a list of images. First image shape: {img[0].shape}")
        
        # 如果rec_model_dir为None，强制禁用文本识别
        if not self.enable_rec:
            if rec:
                logger.warning("Recognition disabled because recognition model is not available")
                rec = False
            if not det:
                logger.warning("Both detection and recognition are disabled. No OCR will be performed.")
                return []

        if cls == True and self.use_angle_cls == False:
            logger.warning("Since the angle classifier is not initialized, the angle classifier will not be used during the forward process")

        # 检测和识别路径
        if det and rec:
            logger.info("Using detection + recognition path")
            ocr_res = []
            
            call_start = time.time()
            dt_boxes, rec_res = self.__call__(img, cls)
            call_time = time.time() - call_start
            logger.info(f"__call__ completed in {call_time:.3f}s")
            
            if dt_boxes is not None and len(dt_boxes) > 0:
                logger.info(f"Detected {len(dt_boxes)} text regions")
                
                # 记录识别结果
                for i, (box, res) in enumerate(zip(dt_boxes, rec_res)):
                    text, confidence = res
                    x_min, y_min = np.min(box, axis=0)
                    x_max, y_max = np.max(box, axis=0)
                    logger.info(f"Region {i+1}: '{text}' (confidence: {confidence:.4f}) at [{x_min:.1f}, {y_min:.1f}, {x_max:.1f}, {y_max:.1f}]")
            else:
                logger.info("No text regions detected")
                
            tmp_res = [[box.tolist(), res] for box, res in zip(dt_boxes, rec_res)]
            ocr_res.append(tmp_res)
            
            total_time = time.time() - start_time
            logger.info(f"OCR completed in {total_time:.3f}s with {len(dt_boxes)} text regions")
            return ocr_res
            
        # 仅检测路径
        elif det and not rec:
            logger.info("Using detection-only path")
            ocr_res = []
            
            det_start = time.time()
            dt_boxes = self.text_detector(img)
            det_time = time.time() - det_start
            logger.info(f"Text detection completed in {det_time:.3f}s")
            
            if dt_boxes is not None and len(dt_boxes) > 0:
                logger.info(f"Detected {len(dt_boxes)} text regions")
                
                # 记录检测框位置
                for i, box in enumerate(dt_boxes):
                    x_min, y_min = np.min(box, axis=0)
                    x_max, y_max = np.max(box, axis=0)
                    logger.info(f"Region {i+1} at [{x_min:.1f}, {y_min:.1f}, {x_max:.1f}, {y_max:.1f}]")
            else:
                logger.info("No text regions detected")
                
            tmp_res = [box.tolist() for box in dt_boxes]
            ocr_res.append(tmp_res)
            
            total_time = time.time() - start_time
            logger.info(f"Detection-only OCR completed in {total_time:.3f}s")
            return ocr_res
            
        # 仅分类和/或识别路径
        else:
            logger.info("Using classification/recognition-only path")
            ocr_res = []
            cls_res = []

            # 确保img是列表
            if not isinstance(img, list):
                logger.info("Converting single image to list")
                img = [img]
                
            # 分类处理
            if self.use_angle_cls and cls:
                logger.info("Performing text classification")
                cls_start = time.time()
                img, cls_res_tmp = self.text_classifier(img)
                cls_time = time.time() - cls_start
                logger.info(f"Classification completed in {cls_time:.3f}s")
                
                if not rec:
                    logger.info("Returning classification results only")
                    cls_res.append(cls_res_tmp)
            
            # 识别处理
            if rec:
                logger.info(f"Performing text recognition on {len(img)} images")
                rec_start = time.time()
                rec_res = self.text_recognizer(img)
                rec_time = time.time() - rec_start
                logger.info(f"Recognition completed in {rec_time:.3f}s")
                
                # 记录识别结果
                for i, res in enumerate(rec_res):
                    text, confidence = res
                    logger.info(f"Text {i+1}: '{text}' (confidence: {confidence:.4f})")
                    
                ocr_res.append(rec_res)

            total_time = time.time() - start_time
            logger.info(f"Classification/recognition-only OCR completed in {total_time:.3f}s")
            
            if not rec:
                return cls_res
            return ocr_res


def sav2Img(org_img, result, name="draw_ocr.jpg"):
    # 显示结果
    from PIL import Image

    result = result[0]
    # image = Image.open(img_path).convert('RGB')
    # 图像转BGR2RGB
    image = org_img[:, :, ::-1]
    boxes = [line[0] for line in result]
    txts = [line[1][0] for line in result]
    scores = [line[1][1] for line in result]
    im_show = draw_ocr(image, boxes, txts, scores)
    im_show = Image.fromarray(im_show)
    im_show.save(name)


if __name__ == "__main__":
    import cv2

    model = ONNXPaddleOcr(use_angle_cls=True, use_gpu=False)

    img = cv2.imread(
        "/data2/liujingsong3/fiber_box/test/img/20230531230052008263304.jpg"
    )
    s = time.time()
    result = model.ocr(img)
    e = time.time()
    print("total time: {:.3f}".format(e - s))
    print("result:", result)
    for box in result[0]:
        print(box)

    sav2Img(img, result)
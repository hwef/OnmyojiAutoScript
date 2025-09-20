import time
import numpy as np

from module.logger import logger
from .predict_system import TextSystem
from .utils import infer_args as init_args
from .utils import str2bool, draw_ocr
import argparse
import sys
from typing import List

class ONNXPaddleOcr(TextSystem):
    def __init__(self, **kwargs):
        logger.info("初始化ONNX PaddleOCR系统")
        start_time = time.time()
        
        # 默认参数
        parser = init_args()
        inference_args_dict = {}
        for action in parser._actions:
            inference_args_dict[action.dest] = action.default
        params = argparse.Namespace(**inference_args_dict)

        # 设置识别模型的图像形状
        params.rec_image_shape = "3, 48, 320"
        
        # 根据传入的参数覆盖更新默认参数
        params.__dict__.update(**kwargs)

        # 检查rec_model_dir是否为None
        self.enable_rec = params.rec_model_dir is not None
        if not self.enable_rec:
            logger.warning("未提供识别模型目录，文本识别功能将被禁用")
            
        # 初始化模型
        super().__init__(params)
        
        init_time = time.time() - start_time
        logger.info(f"ONNX PaddleOCR初始化完成，耗时{init_time:.3f}秒")

    def ocr(self, img, det=True, rec=True, cls=True):
        start_time = time.time()
        
        # 如果rec_model_dir为None，强制禁用文本识别
        if not self.enable_rec:
            if rec:
                logger.warning("识别模型不可用，已禁用文本识别")
                rec = False
            if not det:
                return []

        if cls == True and self.use_angle_cls == False:
            cls = False

        # 检测和识别路径
        if det and rec:
            ocr_res = []
            dt_boxes, rec_res = self.__call__(img, cls)
            
            if dt_boxes is not None and len(dt_boxes) > 0:
                logger.info(f"检测到{len(dt_boxes)}个文本区域")
            else:
                logger.info("未检测到文本区域")
                
            tmp_res = [[box.tolist(), res] for box, res in zip(dt_boxes, rec_res)]
            ocr_res.append(tmp_res)
            
            total_time = time.time() - start_time
            return ocr_res
            
        # 仅检测路径
        elif det and not rec:
            ocr_res = []
            dt_boxes = self.text_detector(img)
            
            if dt_boxes is not None and len(dt_boxes) > 0:
                logger.info(f"检测到{len(dt_boxes)}个文本区域")
            else:
                logger.info("未检测到文本区域")
                
            tmp_res = [box.tolist() for box in dt_boxes]
            ocr_res.append(tmp_res)
            
            return ocr_res
            
        # 仅分类和/或识别路径
        else:
            ocr_res = []
            cls_res = []

            # 确保img是列表
            if not isinstance(img, list):
                img = [img]
                
            # 分类处理
            if self.use_angle_cls and cls:
                img, cls_res_tmp = self.text_classifier(img)
                
                if not rec:
                    cls_res.append(cls_res_tmp)
            
            # 识别处理
            if rec:
                rec_res = self.text_recognizer(img)
                ocr_res.append(rec_res)
            
            if not rec:
                return cls_res
            return ocr_res

    def detect_and_ocr(self, image) -> list:
        """
        检测并识别图像中的文本
        参数:
            image: 输入图像(numpy数组)
        返回:
            包含BoxedResult对象的列表
        """
        from ppocronnx.predict_system import BoxedResult
        from typing import List
        
        try:
            results = []
            ocr_output = self.ocr(image, det=True, rec=True, cls=True)
            
            if not ocr_output or not ocr_output[0]:
                return results
                
            for box_info in ocr_output[0]:
                if len(box_info) != 2:
                    continue
                    
                box = np.array(box_info[0])
                text, score = box_info[1]
                
                # 创建BoxedResult对象
                result = BoxedResult(box=box, text_img=image,ocr_text=text, score=score)
                results.append(result)
                
            return results
        except Exception as e:
            logger.error(f"检测和识别失败: {str(e)}")
            return []

   
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
        r"module\ocr\onnxocr\test_images\1.jpg"
    )
    s = time.time()
    result = model.ocr(img)
    e = time.time()
    print("total time: {:.3f}".format(e - s))
    print("result:", result)
    for box in result[0]:
        print(box)

    # sav2Img(img, result)
    cv2.imshow("test" , img)
    cv2.waitKey(0)
    cv2.destroyWindow("test")
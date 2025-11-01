from deploy.patch import pre_checks

#
pre_checks()

import pickle
from deploy.logger import logger
from module.server.setting import State
import socket


class OcrServer:

    def start_ocr_server(self):

        if State.deploy_config.UseOcrServer:
            port = State.deploy_config.OcrServerPort
        else:
            return

        import zerorpc
        import zmq
        from module.ocr.models import OcrModel

        class OCRServer(OcrModel):
            def hello(self):
                return "hello"

            def ocr(self, img_fp):
                img_fp = pickle.loads(img_fp)
                cnocr = self.__getattribute__('ch')
                return cnocr.ocr(img_fp)

            def detect_and_ocr(self, img_fp, drop_score=None):
                img_fp = pickle.loads(img_fp)
                cnocr = self.__getattribute__('ch')
                results = cnocr.detect_and_ocr(img_fp, drop_score)
                # Convert BoxedResult objects to serializable dictionaries
                if results:
                    return [result.to_dict() for result in results]
                return []

            def ocr_lines(self, img_fp):
                img_fp = pickle.loads(img_fp)
                cnocr = self.__getattribute__('ch')
                return cnocr.ocr_lines(img_fp)

            def ocr_single_line(self, img_fp):
                img_fp = pickle.loads(img_fp)
                cnocr = self.__getattribute__('ch')
                return cnocr.ocr_single_line(img_fp)

        server = zerorpc.Server(OCRServer())
        try:
            server.bind(f"tcp://*:{port}")
        except zmq.error.ZMQError:
            logger.info(f"Ocr server cannot bind on port {port}")
            return
        logger.info(f"[OcrServer] Listening on port {port}")
        server.run()

    def is_ocr_server_running(self, port=22268):
        """检测OCR服务器是否已在运行"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            return result == 0

    def manage_ocr_server_smart(self):
        """智能管理OCR服务器启动"""
        if not self.is_ocr_server_running():
            self.start_ocr_server()
            logger.info("Started new OCR server instance")
        else:
            logger.info("OCR server already running, skipping start")


if __name__ == '__main__':
    OcrServer().start_ocr_server()

import os
import socket
from module.device.execute_util import execute_show_window
from module.logger import logger
from module.server.setting import State


def start_ocr_server_bat():
    # 构建bat文件路径
    bat_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'start_OCR.bat')
    bat_file_path = os.path.abspath(bat_file_path)
    cmd = [bat_file_path]
    logger.info(f"启动OCR服务: {cmd}")
    result = execute_show_window(cmd)
    # logger.info(f"启动OCR服务结果: {result}")


def check_ocr_server_process():
    """检测OCR服务器是否已在运行"""
    if State.deploy_config.UseOcrServer:
        port = State.deploy_config.OcrServerPort
    else:
        logger.info("OCR 服务未启用")
        return

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        result = sock.connect_ex(('localhost', port))
        return result == 0

import threading
import websocket
import sys
import logging
import os
import time
import urllib.parse
import io


def start_websocket(config_name, command: str = "start"):
    # 日志配置部分保持不变...
    log_dir = rf".\log"

    # 确保日志目录存在
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置文件处理器为 UTF-8 编码
    file_handler = logging.FileHandler(
        os.path.join(log_dir, f"log_{config_name}.log"), 
        encoding='utf-8'
    )
    
    # 配置控制台处理器，处理编码问题
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                super().emit(record)
            except UnicodeEncodeError:
                # 如果遇到编码错误，过滤掉无法编码的字符
                original_message = record.getMessage()
                # 尝试编码为 GBK，忽略错误字符
                safe_message = original_message.encode('gbk', errors='ignore').decode('gbk')
                record.msg = safe_message
                super().emit(record)
    
    stream_handler = SafeStreamHandler(sys.stdout)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[file_handler, stream_handler],
        force=True
    )
    logging.info("日志配置成功！")

    logging.info(f"[{config_name}] 尝试连接到WebSocket")
    config_name = urllib.parse.quote(config_name)
    ws = websocket.WebSocketApp(f"ws://127.0.0.1:22288/ws/{config_name}")

    # 处理 WebSocket 连接打开事件
    def on_open(ws):
        logging.info(f"[{config_name}] WebSocket连接成功!")
        ws.send(command)
        logging.info(f"已发送: {command}")

    # 处理接收到的消息
    def on_message(ws, response):
        # 处理可能包含特殊字符的响应
        try:
            logging.info(f"收到响应: {response}")
        except UnicodeEncodeError:
            # 如果仍然有编码错误，安全地处理它
            safe_response = response.encode('gbk', errors='ignore').decode('gbk')
            logging.info(f"收到响应: {safe_response}")

    # 设置 WebSocket 回调函数
    ws.on_open = on_open
    ws.on_message = on_message

    # 设置超时退出
    def exit_timer():
        logging.info("超时关闭连接...")
        ws.close()
        sys.exit(0)

    timer = threading.Timer(5, exit_timer)  # 30秒后自动关闭
    timer.start()

    ws.run_forever()
    timer.cancel()  # 如果连接正常关闭，取消定时器


if __name__ == "__main__":
    # 保证通过命令行运行时传入参数，例如：python script.py MI

    config_name = sys.argv[1]
    # config_name = "DU"
    # command = "get_state"
    # command = "get_schedule"
    command = "start"
    # command = "stop"
    print(f'[{config_name}]启动...')
    start_websocket(config_name, command)

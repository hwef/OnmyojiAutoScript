import threading
import websocket
import sys
import logging
import os
import time
import urllib.parse
import io
import json


def start_websocket(config_name, command: str = "start"):

    # 日志配置部分保持不变...
    log_file = rf"D:\OnmyojiAutoScript\ljxun\log\log_{config_name}.log"

    # 配置日志：通过 handlers 实现文件+控制台输出
    file_handler = logging.FileHandler(log_file)
    stream_handler = logging.StreamHandler(sys.stdout)  # 输出到控制台

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[file_handler, stream_handler]
    )
    logging.info("日志配置成功！")

    logging.info(f"[{config_name}] 尝试连接到WebSocket")
    config_name = urllib.parse.quote(config_name)
    url = f"ws://127.0.0.1:22288/ws/{config_name}"
    logging.info(f"[{config_name}] WebSocket URL: {url}")
    ws = websocket.WebSocketApp(url)

    # 处理 WebSocket 连接打开事件
    def on_open(ws):
        logging.info(f"[{config_name}] WebSocket连接成功!")
        ws.send(command)
        logging.info(f"已发送: {command}")

    # 处理接收到的消息
    def on_message(ws, response):
        print(f"收到响应: {response}")

        if 'schedule' in response:
            data = json.loads(response)
            schedule = data['schedule']
            if 'running' in schedule and schedule['running']:
                running_task = schedule['running']
                logging.info(f"[{config_name}] 当前运行任务: {running_task['name']}")
            else:
                logging.info(f"[{config_name}] 当前无运行任务")
        if 'state' in response:
            data = json.loads(response)
            state = data['state']
            if state == 1:
                logging.info(f"[{config_name}] 当前运行中")
            elif state == 0:
                logging.info(f"[{config_name}] 当前已停止")

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

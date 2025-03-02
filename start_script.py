from sys import argv

import threading
import time
import websocket


def on_open(ws):
    print("连接已建立")
    ws.send("start")  # 可选：发送初始消息


def on_message(ws, message):
    # print(f"收到消息: {message}")
    pass


def on_error(ws, error):
    print(f"发生错误: {error}")
    print(f"重启进程")
    ws.send("stop")
    time.sleep(2)
    ws.send("start")


def on_close(ws, close_status_code, close_msg):
    print(f"连接关闭: 状态码={close_status_code}, 消息='{close_msg}'")


def main(config_name):
    # config_name = "du"
    server_address = f"ws://127.0.0.1:22288/ws/{config_name}"

    # 创建 WebSocket 对象
    ws = websocket.WebSocketApp(
        server_address,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # 启动 WebSocket 事件循环线程
    wst = threading.Thread(target=ws.run_forever)
    wst.start()

    # 设置 60 秒后强制关闭连接的定时器
    # def force_close():
    #     print("60 秒超时，强制关闭连接...")
    #     if ws.sock and ws.sock.connected:  # 检查连接状态
    #         ws.close()
    #
    # # 使用线程安全的定时器（非阻塞主线程）
    # timer = threading.Timer(60, force_close)
    # timer.start()

    # 主线程等待（可选：手动控制关闭）
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
        # print("用户中断，正在关闭连接...")
        # timer.cancel()  # 取消定时器
        # ws.close()


if __name__ == "__main__":
    sleep_time = 5
    time.sleep(sleep_time)
    print(f'{argv[1]}等待{sleep_time}秒后启动')
    main(argv[1])

import asyncio
import sys
import websockets
from websockets.exceptions import ConnectionClosedError, InvalidURI
import time

async def main(config_name):
    server_address = f"ws://127.0.0.1:22288/ws/{config_name}"
    close_event = asyncio.Event()
    max_retries = 5  # 最大重试次数
    retry_delay = 10  # 初始重试延迟（秒）

    async def connect_with_retry():
        nonlocal retry_delay
        for attempt in range(1, max_retries + 1):
            try:
                async with websockets.connect(server_address) as websocket:
                    print(f"尝试 #{attempt}：连接已建立")
                    await websocket.send("start")
                    
                    # 持续接收消息，带接收超时
                    while not close_event.is_set():
                        try:
                            message = await asyncio.wait_for(
                                websocket.recv(),
                                timeout=5  # 消息接收超时时间
                            )
                            print(f"收到消息: {message}")
                        except asyncio.TimeoutError:
                            print("⏳ 接收消息超时，保持连接...")
                            await asyncio.sleep(1)
                            
            except (ConnectionRefusedError, InvalidURI) as e:
                print(f"❌ 尝试 #{attempt} 失败：{e}")
                if attempt < max_retries:
                    wait_time = retry_delay * (2 ** (attempt-1))
                    print(f"🔄 {wait_time}秒后重试...")
                    await asyncio.sleep(wait_time)
                    retry_delay = wait_time  # 动态调整重试间隔
            except ConnectionClosedError as e:
                print(f"⚠️ 连接意外关闭：状态码={e.code}, 原因={e.reason}")
                break
            except Exception as e:
                print(f"⚠️ 发生未预期错误：{str(e)}")
                break
            else:
                # 连接正常关闭时退出重试循环
                break
            finally:
                if attempt < max_retries:
                    retry_delay *= 2  # 指数退避

        close_event.set()  # 确保最终标记关闭

    try:
        # 主任务带总超时控制
        await asyncio.wait_for(connect_with_retry(), timeout=60)
    except asyncio.TimeoutError:
        print("\n🕒 总连接超时，已尝试所有重试机会")
    finally:
        print("\n🔌 正在清理资源...")
        await asyncio.sleep(0.1)  # 确保协程结束

if __name__ == "__main__":
    time.sleep(5)  # 启动延迟
    try:
        asyncio.run(main(sys.argv[1]))
    except KeyboardInterrupt:
        print("\n🚨 用户中断操作")
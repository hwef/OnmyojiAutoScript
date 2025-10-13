import requests
from datetime import datetime

def send_put_request():
    """
    发送PUT请求到指定URL
    """

    script_name = "du"
    ip = "http://127.0.0.1:22288"
    # ip = "http://1a84o56629.zicp.fun"
    taskk = "Orochi"

    # 获取当前时间
    current_time = datetime.now()
    # 格式化时间为指定格式
    formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

    print(formatted_time)

    # 请求URL - 根据服务器端API规范构造URL
    # 服务器端API: /{script_name}/{task}/{group}/{argument}/value
    url = f"{ip}/{script_name}/{taskk}/scheduler/next_run/value"
    
    # 请求参数作为查询参数
    params = {
        'types': 'date_time',
        'value': formatted_time
    }

    # 请求头
    headers = {
        'Accept': 'application/json'
    }

    try:
        # 发送PUT请求，将参数作为查询参数传递
        response = requests.put(url, params=params, headers=headers)

        # 输出请求信息
        print(f"请求URL: {url}")
        print(f"请求方法: PUT")
        print(f"请求参数: {params}")
        print(f"状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        print(f"响应头: {response.headers}")

        # 检查请求是否成功
        if response.status_code == 200:
            print("请求成功!")
        else:
            print(f"请求失败，状态码: {response.status_code}")
            if response.status_code == 404:
                print("请检查URL路径是否正确")
            elif response.status_code == 500:
                print("服务器内部错误，请检查服务器日志")

    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

def fetch_today_data():
    """
    请求 https://fetchbuild.luckyancj.site/today 并接收返回消息
    """
    url = "https://fetchbuild.luckyancj.site/today"

    try:
        # 发送GET请求
        response = requests.get(url)

        # 输出请求信息
        print(f"请求URL: {url}")
        print(f"请求方法: GET")
        print(f"状态码: {response.status_code}")

        # 检查请求是否成功
        if response.status_code == 200:
            print("请求成功!")
            print(f"响应内容: {response.text}")

            # 如果返回的是JSON格式数据
            try:
                json_data = response.json()
                print(f"JSON响应: {json_data}")
            except ValueError:
                print("响应不是有效的JSON格式")

        else:
            print(f"请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")



if __name__ == "__main__":
    # print("=== 发送PUT请求 ===")
    # send_put_request()
    print("=== 请求今日数据 ===")
    fetch_today_data()
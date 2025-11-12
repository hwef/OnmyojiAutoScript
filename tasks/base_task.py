# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

from time import sleep

import cv2
import os
import requests
from datetime import datetime, timedelta
from fuzzywuzzy import fuzz
from module.atom.image import RuleImage
from module.base.timer import Timer
from module.config.config_model import ConfigModel
from module.exception import TaskEnd
from module.logger import logger, log_path, week_path, get_filename
from module.server.i18n import I18n
from numpy import uint8, fromfile
from pathlib import Path
from tasks.Component.config_base import Time
from tasks.base_task_parent import BaseTaskParent


class BaseTask(BaseTaskParent):

    def load_image(self, file: str):
        file = Path(file)
        img = cv2.imdecode(fromfile(file, dtype=uint8), -1)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        height, width, channels = img.shape
        if height != 720 or width != 1280:
            logger.error(f'Image size is {height}x{width}, not 720x1280')
            return None
        return img

    def get_rgb_from_target(self, target: tuple):
        """
        从传入的目标区域提取平均RGB值
        参数:
        - target: 目标区域 (x, y, width, height)
        返回:
        - 平均RGB值 (R, G, B)
        """
        x, y, w, h = target.roi_front
        # 截图并获取设备当前图像
        image = self.device.image

        # 提取目标区域的图像
        region = image[y:y + h, x:x + w]

        # 计算平均RGB值
        average_color = cv2.mean(region)[:3]  # 只取前三个值 (B, G, R)

        logger.info(f"目标区域 [{target.roi_front}] 的RGB值为: {average_color}")
        return average_color

    def appear_rgb(self, target, image=None, difference: int = 10):
        """
        判断目标的平均颜色是否与图像中的颜色匹配。
        参数:
        - target: 目标对象，包含目标的文件路径和区域信息。
        - image: 输入图像，如果未提供，则使用设备捕获的图像。
        - difference: 颜色差异阈值，默认为10。
        返回:
        - 如果目标颜色与图像颜色匹配，则返回True，否则返回False。
        """
        # 如果未提供图像，则使用设备捕获的图像
        # logger.info(f"target [{target}], image [{image}]")
        if not self.appear(target):
            logger.warning(f"[{target.name}]未匹配到")
            return False

        if image is None:
            image = self.device.image

        # 加载图像并计算其平均颜色
        img = cv2.imread(target.file)
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        average_color = cv2.mean(img_rgb)
        # logger.info(f"[{target.name}]average_color: {average_color}")

        # 提取目标区域的坐标和尺寸，并确保它们为整数
        x, y, w, h = target.roi_front
        x, y, w, h = int(x), int(y), int(w), int(h)
        # 从输入图像中提取目标区域
        img = image[y:y + h, x:x + w]
        # 计算目标区域的平均颜色
        color = cv2.mean(img)
        # logger.info(f"[{target.name}] color: {color}")

        # 比较目标图像和目标区域的颜色差异
        for i in range(3):
            if abs(average_color[i] - color[i]) > difference:
                logger.warning(f" [{target.name}] 颜色匹配失败")
                return False

        logger.info(f"[{target.name}] 颜色匹配成功")
        return True

    def save_image(self, task_name=None, content=None, wait_time=2, image_type=False, push_flag=False):
        try:
            # 小号配置检查
            con = self.config.switch_account_config.config
            if con.enable:
                if not con.enable_save_image:
                    if content:
                        logger.info(content)
                    logger.warning(f"未启用账号截图保存")
                    return
                name = con.account_name
                filename = get_filename(name)
            else:
                filename = get_filename(self.config.config_name.upper())

            # 获取任务名称
            if task_name is None:
                task_name = "task_name"
                if self.config and self.config.task:
                    task_name = self.config.task.command

            # 截图等待时间
            if wait_time > 0:
                sleep(wait_time)
                self.screenshot()

            # 使用getattr同时检查属性和值，避免冗长的条件判断
            if getattr(self.device, 'image', None) is None:
                self.screenshot()

            image = cv2.cvtColor(self.device.image, cv2.COLOR_BGR2RGB)

            # 设置保存图像的文件夹 - 使用类属性或配置中的weekly task列表
            if not hasattr(self, '_weekly_task_cache'):
                from module.config.config_menu import ConfigMenu
                self._weekly_task_cache = ConfigMenu().menu["Weekly Task"]
                print(isinstance(self._weekly_task_cache, list))

            path = f"{I18n.trans_zh_cn(task_name)}/{self.config.config_name.upper()}"
            if task_name in self._weekly_task_cache:
                folder_name = f'{week_path}/{path}'
            else:
                folder_name = f'{log_path}/{path}'

            folder_path = Path(folder_name)
            folder_path.mkdir(parents=True, exist_ok=True)
            image_path = folder_path / filename  # 使用pathlib路径对象

            if image_type:
                # 保存图像正常大小
                image_path = image_path.with_suffix('.png')
                params = []
            else:
                # 修改图像为.webp格式, 调整图像分辨率原来的一半
                image_path = image_path.with_suffix('.webp')
                # 调整图像分辨率
                scale_percent = 50  # 缩放到原来的一半
                width = int(image.shape[1] * scale_percent / 100)
                height = int(image.shape[0] * scale_percent / 100)
                dim = (width, height)
                image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
                # 调整图像质量并保存为WebP格式
                params = [int(cv2.IMWRITE_WEBP_QUALITY), 50]

            # 使用cv2.imencode+文件流保存（解决中文路径问题）
            ext = image_path.suffix
            ret, buf = cv2.imencode(ext, image, params)
            if ret:
                with open(image_path, 'wb') as f:
                    f.write(buf.tobytes())
                logger.info(f"截图已保存至：{image_path}")
                if push_flag:
                    self.push_notify(content=content if content else f"截图已保存至：{image_path}")
                else:
                    if content:
                        logger.info(content)
            else:
                self.push_notify(content=f"保存{image_path}, 图像编码失败")
                raise Exception("图像编码失败")
        except Exception as e:
            self.push_notify(content=f"保存截图异常，{e}")
            logger.error(f"保存{task_name}截图异常，{e}")

    def push_notify(self, content='', title=None):

        if content != '':
            logger.info(content)

        # 处理title的逻辑优化
        if not title:
            if self.config and self.config.task:
                title = self.config.task.command
            else:
                title = 'task_name'

        con = self.config.switch_account_config.config
        if con.enable:
            if not con.enable_push_notify:
                logger.warning(f"未启用账号消息推送")
                return
            name = con.account_name
            logger.info(f"已开启小号任务，并启用了小号通知，拼接[{name}]，准备发送通知")
            title = f"{name}▪{I18n.trans_zh_cn(title)}"

        # 使用getattr同时检查属性和值，避免冗长的条件判断
        if self.emulator.is_emulator_running() and getattr(self.device, 'image', None) is not None:
            image = self.device.image
        else:
            image = ""

        # 发送邮件
        self.config.notifier.send_push(title=title, content=content, image=image)

    def ocr_text_threshold(self, target, threshold=0.7, interval: float = None):
        if interval:
            if target.name in self.interval_timer:
                # 如果传入的限制时间不一样，则替换限制新的传入的时间
                if self.interval_timer[target.name].limit != interval:
                    self.interval_timer[target.name] = Timer(interval)
            else:
                # 如果没有限制时间，则创建限制时间
                self.interval_timer[target.name] = Timer(interval)
                # 如果时间还没到达，则不执行
            if not self.interval_timer[target.name].reached():
                return None

        appear = False

        ocrResult = target.ocr(self.device.image)
        # 边界检查：确保 OCR 结果不为空
        if not ocrResult or len(ocrResult) == 0:
            return False
        if self.assess_text_threshold(target.keyword, ocrResult, threshold):
            appear = True
        if interval and appear:
            self.interval_timer[target.name].reset()
        return appear

    def assess_text_threshold(self, old_str, new_str, threshold=0.7):
        threshold_pct = threshold * 100
        similarity_score = fuzz.ratio(old_str, new_str)
        if similarity_score >= threshold_pct:
            logger.info(f"✅ [{old_str}] vs [{new_str}], 相似度 {similarity_score}% ≥ {threshold_pct}%, 匹配成功")
            return True
        else:
            logger.info(f"❌ [{old_str}] vs [{new_str}], 相似度 {similarity_score}% < {threshold_pct}%, 匹配失败")
            return False

    def split_group_team(self, target):
        if isinstance(target, str):
            try:
                parts = target.split(',')
                if len(parts) != 2:
                    raise ValueError('Switch_str must be 2 parts')
                return int(parts[0]), int(parts[1])
            except ValueError:
                logger.error(f'Invalid switch_group_team format: {target}')
                return -1, -1
        return -1, -1

    def _load_image_template(self, image_folder, threshold=0.8):
        image_templates = []
        supported_formats = ('.png', '.jpg', '.jpeg')

        # 遍历图片文件夹
        for filename in os.listdir(image_folder):
            if not filename.lower().endswith(supported_formats):
                continue
            # 构建完整路径
            file_path = os.path.join(image_folder, filename)

            # 创建RuleImage对象并添加到列表
            image_rule = RuleImage(
                roi_front=(0, 0, 1280, 720),  # 保持与原来相同的ROI参数
                roi_back=(0, 0, 1280, 720),
                threshold=threshold,
                method="Template matching",
                file=file_path
            )
            image_templates.append(image_rule)

        logger.info(f"加载图片模板集合: {image_templates}")
        logger.info(f"加载图片模板数量: {len(image_templates)}")
        return image_templates

    def _check_first_priority_task(self):
        self.config.model = ConfigModel(config_name=self.config.config_name)
        self.config.get_next()
        first_priority_task = self.config.first_priority_task
        current_task = self.config.task.command
        if first_priority_task != current_task:
            logger.warning(f"结束当前任务: {I18n.trans_zh_cn(current_task)}")
            logger.warning(f"执行优先任务: {I18n.trans_zh_cn(first_priority_task)}")
            raise TaskEnd

    def get_requests(self, url):
        try:
            # 发送GET请求
            response = requests.get(url)
            logger.info(f"响应内容: {response.text}")
            # 检查请求是否成功
            if response.status_code == 200:
                return response
            else:
                logger.info(f"请求失败，状态码: {response.status_code}")
                self.push_notify(title="请求失败", content=f"状态码: {response.status_code}")
                return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"请求发生错误: {e}")
            self.push_notify(title="请求发生错误", content=f"{e}")
            return ""

    def datetime_add_timedelta(self, time_interval: Time, base_time: datetime = None) -> datetime:
        """
        将 Time 类型对象转换为 timedelta 并加到指定的 datetime 对象上
        参数:
        base_time (datetime): 基础时间对象
        time_interval (Time): Time 类型的时间间隔对象
        返回:
        datetime: 累加后的时间对象
        """
        if base_time is None:
            base_time = datetime.now()
        time_delta = timedelta(hours=time_interval.hour, minutes=time_interval.minute, seconds=time_interval.second)
        return base_time + time_delta


if __name__ == '__main__':
    from module.config.config import Config

    c = Config('du')
    t = BaseTask(c)
    # t.next_run_week(4)
    # t.next_run_week(2)
    # t.push_notify("123456", "123456",1)
    # t.next_run_week(c.duel.switch_week.next_week_day)
    # t.save_image(task_name="Duel", push_flag=True, content='成功保存截图')
    # t.save_image(task_name="Orochi", push_flag=True, content='成功保存截图')
    # t.save_image(task_name="TrueOrochi", push_flag=True, content='成功保存截图')
    # t.save_image(task_name="RichMan", push_flag=True, content='成功保存截图')
    # I_E_AUTO_ROTATE_OFF = RuleImage(roi_front=(108,650,150,46), roi_back=(108,650,150,46), threshold=0.85, method="Template matching", file="./tasks/Exploration/res/res_e_auto_rotate_off.png")
    # t.appear_rgb(I_E_AUTO_ROTATE_OFF)

    # self.config.notifier.send_mail(title=task_name, head=head, image_path=image_path)

    # t.push_notify()
    # t.save_image(content='成功找到最优挂卡', push_flag=True)
    # card_type = '斗鱼'
    # card_value = '118'
    # t.save_image(push_flag=True, wait_time=0, content=f'🎉 确认蹭卡 ({card_type}: {card_value})')
    # logger.hr('INVITE FRIEND')
    # logger.hr('INVITE FRIEND', 0)
    # logger.hr('INVITE FRIEND', 1)
    # logger.hr('INVITE FRIEND', 2)
    # logger.hr('INVITE FRIEND', 3)
    # logger.hr('INVITE FRIEND')

    # datetime_now = datetime.now().strftime("%A")
    # logger.info(datetime_now)

    # # 获取当前日期
    # today = date.today()
    # # 获取星期几，返回值为 0（周一）到 6（周日）
    # weekday = today.weekday()
    # # 将数字转换为星期几的名称
    # weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    # print("今天是：", weekdays[weekday])

# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import base64
from email.message import EmailMessage

import aiohttp
import asyncio

import cv2
import onepush.core
import yaml
from aiohttp_socks import ProxyConnector
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from numpy import fromfile, uint8
from pydoc import html
from smtplib import SMTPResponseException

from module.logger import logger
from onepush import get_notifier
from onepush.core import Provider
from onepush.exceptions import OnePushException
from onepush.providers.custom import Custom
from requests import Response
from pathlib import Path
from onepush.providers.smtp import SMTP, _default_message_parser

from module.server.i18n import I18n

onepush.core.log = logger


class Notifier:
    def __init__(self, _config: str, _config_tg: str, enable: bool = False, enable_tg: bool = False) -> None:
        self.config_name: str = ""
        self.enable: bool = enable
        self.enable_tg: bool = enable_tg

        if self.enable:
            config = {}
            try:
                for item in yaml.safe_load_all(_config):
                    config.update(item)
            except Exception as e:
                logger.error("Fail to load onepush config, skip sending")
                return
            self.config = config
            try:
                # 获取provider
                self.provider_name: str = self.config.pop("provider", "")
                if self.provider_name == "":
                    logger.info("No provider specified, skip sending")
                    return
                # 获取notifier
                self.notifier: Provider = get_notifier(self.provider_name)
                # 获取notifier的必填参数
                self.required: list[str] = self.notifier.params["required"]
            except OnePushException:
                logger.exception("Init notifier failed")
                return
            except Exception as e:
                logger.exception(e)
                return

        if self.enable_tg:
            config_tg = {}
            try:
                for item in yaml.safe_load_all(_config_tg):
                    config_tg.update(item)
            except Exception as e:
                logger.error("Fail to load onepush config, skip sending")
                return
            self.config_tg = config_tg
            try:
                self.proxy: str = self.config_tg.pop("proxy", "")
                if self.proxy == "":
                    logger.info("No proxy specified, skip sending")
                    return
                self.token: str = self.config_tg.pop("token", "")
                if self.token == "":
                    logger.info("No token specified, skip sending")
                    return
                self.chat_id: str = self.config_tg.pop("chat_id", "")
                if self.chat_id == "":
                    logger.info("No chat_id specified, skip sending")
                    return
            except Exception as e:
                logger.error(e)
                return

    def push(self, **kwargs) -> bool:
        title = f"{self.config_name}▪{I18n.trans_zh_cn(kwargs['title'])}"
        if not ("type" in kwargs and kwargs["type"] == "mail"):
            content = kwargs["content"]
            title = f"{title} | {content}"
        asyncio.run(self.send_text_message(title))
        if not self.enable:
            return False
        # 更新配置
        kwargs["title"] = title.replace(' ', '\u00A0')
        self.config.update(kwargs)
        # pre check
        for key in self.required:
            if key not in self.config:
                logger.warning(f"Notifier {self.notifier} require param '{key}' but not provided")

        if isinstance(self.notifier, Custom):
            if "method" not in self.config or self.config["method"] == "post":
                self.config["datatype"] = "json"
            if not ("data" in self.config or isinstance(self.config["data"], dict)):
                self.config["data"] = {}
            if "title" in kwargs:
                self.config["data"]["title"] = kwargs["title"]
            if "content" in kwargs:
                self.config["data"]["content"] = kwargs["content"]

        if self.provider_name.lower() == "gocqhttp":
            access_token = self.config.get("access_token")
            if access_token:
                self.config["token"] = access_token

        try:
            resp = self.notifier.notify(**self.config)
            if isinstance(resp, Response):
                if resp.status_code != 200:
                    logger.warning("Push notify failed!")
                    logger.warning(f"HTTP Code:{resp.status_code}")
                    return False
                else:
                    if self.provider_name.lower() == "gocqhttp":
                        return_data: dict = resp.json()
                        if return_data["status"] == "failed":
                            logger.warning("Push notify failed!")
                            logger.warning(
                                f"Return message:{return_data['wording']}")
                            return False
        except OnePushException:
            logger.exception("Push notify failed")
            return False
        except SMTPResponseException:
            logger.warning("Appear SMTPResponseException")
            pass
        except Exception as e:
            logger.exception(e)
            return False
        logger.info("Push notify success")
        return True

    async def send_text_message(self, text: str, timeout: int = 10) -> bool:
        if not self.enable_tg:
            return False
        proxy = self.proxy
        token = self.token
        chat_id = str(self.chat_id)

        """发送纯文本消息"""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}

        try:
            connector = None
            if proxy and proxy.startswith("socks"):
                connector = ProxyConnector.from_url(proxy)

            async with aiohttp.ClientSession(connector=connector) as session:
                kwargs = {"proxy": proxy} if proxy and not connector else {}

                async with session.post(
                        url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        **kwargs
                ) as response:
                    result = await response.json()
                    return result.get("ok", False)

        except Exception as e:
            logger.error(f"发送文本失败: {str(e)}")
            return False

    def send_mail(self, title: str, head: str, image_path: str, log_path: str):
        """
        发送消息，包括标题、头部、图片和日志内容。

        参数:
        - title (str): 消息标题
        - head (str): 消息头部文字
        - image_path (str): 图片文件路径
        - log_path (str): 日志文件路径

        返回:
        - 成功时返回 HTML 推送的结果，失败时返回普通推送的结果。
        """
        try:
            # 读取日志文件内容
            content = Path(log_path).read_text(encoding='utf-8')

            # 读取并处理图片
            image = Path(image_path)
            image = cv2.imdecode(fromfile(image, dtype=uint8), -1)
            image = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
            img_str = cv2.imencode('.png', image)[1].tobytes()
            b64_code = base64.b64encode(img_str)
            b64_code = b64_code.decode()

            # 格式化头部、图片和日志内容为 HTML
            head_text = f'<b>{head}</b><br/><br/>'
            image_b64 = f'<img src="data:image/png;base64,{b64_code}" alt="image" /><br/><br/>'
            content_text = ''.join(
                f'<p style="font-size:8px;">{item}</p>'
                for item in content.splitlines()
            )
            body = head_text + image_b64 + content_text

            # 返回 HTML 内容的推送结果
            return self.push_html(title=f'{I18n.trans_zh_cn(title)} | {head}', content=body)
        except Exception as e:
            # 记录异常错误
            logger.error(f"出现异常: {e}")
            # 备用方案：发送普通消息
            return self.push(title=title, content=head)

    def push_html(self, **kwargs):
        SMTP.set_message_parser(self.custom_parse)
        kwargs["type"] = "mail"
        self.push(**kwargs)
        SMTP.set_message_parser(_default_message_parser)

    def custom_parse(self, subject: str = '', title: str = '', content: str = '', From: str = None, user: str = None,
                     To: str = None, **kwargs, ):
        msg = EmailMessage()
        # Use subject if avaliable, title for compatibility with other providers
        msg["Subject"] = subject or title
        # Fallback to username if `From` address not provided
        msg["From"] = From or user
        # Send to yourself if `To` address not provided
        msg["To"] = To or user

        msg.set_content(content, subtype='html', charset='utf-8')  # 关键修改点
        return msg



if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    config = Config('du')
    device = Device(config)
    image_path = r"D:\OnmyojiAutoScript\ljxun\log\backup\2025-03-30 星期日\error\MI 09-10-40 (2025-03-30).png"
    log_path = r"D:\OnmyojiAutoScript\ljxun\log\backup\2025-03-30 星期日\error\MI 09-10-40 (2025-03-30).log1"
    # config.notifier.send_mail(title='BondlingFairyland', head='契灵数量已达上限500，请及时处理', image_path=image_path, log_path=log_path)
    config.notifier.push(title='Dokan', content='Dokan，请及时处理')

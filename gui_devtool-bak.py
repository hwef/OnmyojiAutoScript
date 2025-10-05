from tkinter import filedialog

import customtkinter as ctk
import cv2
import json
import numpy as np
import os
import subprocess
from PIL import Image, ImageTk
from datetime import datetime
import pyperclip
from tkinter import messagebox

# 添加模块导入
import sys
from pathlib import Path
import re
# 将当前目录加入系统路径，以便导入项目模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# 尝试导入项目模块
try:
    from module.atom.image import RuleImage
    from module.atom.ocr import RuleOcr
    MODULE_AVAILABLE = True
except ImportError:
    MODULE_AVAILABLE = False
    print("无法导入项目模块，部分功能将不可用")

# 添加对 mask_generator 的导入
try:
    from mask_generator import MaskGenerator
    MASK_GENERATOR_AVAILABLE = True
except ImportError:
    MASK_GENERATOR_AVAILABLE = False
    print("无法导入蒙版生成器模块")

class DevTool(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.last_selected_image = None
        self.last_selected_folder = None
        self.np_image = None  # 截图的 NumPy 图像
        self.current_image = None  # 当前显示的图像
        self.rect = {"x1": 0, "y1": 0, "x2": 0, "y2": 0}  # 矩形框
        self.img_info = None  # 保存图片信息
        # 创建窗口
        self.geometry("1730x780")  # 增加窗口宽度和高度
        self.title("DevTool")
        self.resizable(False, False)

        # 设置默认路径
        self.screenshots_path = r"D:\共享文件夹\Screenshots"
        self.save_img_path = r"D:\共享文件夹\Screenshots"

        # 确保默认路径存在
        if not os.path.exists(self.screenshots_path):
            try:
                os.makedirs(self.screenshots_path)
            except:
                self.screenshots_path = os.getcwd()  # 如果创建失败，使用当前目录

        if not os.path.exists(self.save_img_path):
            try:
                os.makedirs(self.save_img_path)
            except:
                self.save_img_path = os.getcwd()  # 如果创建失败，使用当前目录

        # 创建主框架以支持更好的布局
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 配置网格权重以支持调整大小
        # 保持画布区域固定尺寸
        self.main_frame.grid_columnconfigure(0, weight=0)
        self.main_frame.grid_columnconfigure(1, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # 创建画布框架
        self.canvas_frame = ctk.CTkFrame(self.main_frame)
        self.canvas_frame.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="")

        # 创建画布
        self.screen_canvas = ctk.CTkCanvas(self.canvas_frame, width=1280, height=720, bg="white")
        self.screen_canvas.configure(borderwidth=2, relief="solid")
        self.screen_canvas.bind("<Enter>", self.in_canvas)
        self.screen_canvas.bind("<Leave>", self.out_canvas)
        self.screen_canvas.bind("<Button-1>", self.on_click)
        self.screen_canvas.bind("<B1-Motion>", self.on_move)
        self.screen_canvas.bind("<ButtonRelease-1>", self.on_release)
        # 使用固定尺寸，确保画布保持1280x720
        self.screen_canvas.grid(row=0, column=0, padx=10, pady=10)
        self.mouse_is_in_canvas = False

        # 右侧控制面板框架
        self.control_frame = ctk.CTkFrame(self.main_frame, width=300)
        self.control_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        self.control_frame.grid_propagate(False)  # 防止框架根据子控件调整大小
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_rowconfigure(1, weight=1)

        # 创建选项卡视图
        self.tabview = ctk.CTkTabview(self.control_frame, width=200, height=100)
        self.tabview.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="nsew")
        
        # 添加三个选项卡
        self.screenshot_tab = self.tabview.add("截图工具")
        self.template_tab = self.tabview.add("模板匹配")
        self.ocr_tab = self.tabview.add("OCR工具")
        self.tools_tab = self.tabview.add("工具")  # 添加新选项卡
        
        # 配置各选项卡的网格权重
        self.screenshot_tab.grid_columnconfigure(0, weight=1)
        self.screenshot_tab.grid_rowconfigure(10, weight=1)
        self.template_tab.grid_columnconfigure(0, weight=1)
        self.template_tab.grid_columnconfigure(1, weight=0)  # 第1列保持固定
        self.template_tab.grid_columnconfigure(2, weight=0)  # 第2列保持固定
        self.template_tab.grid_rowconfigure(10, weight=1)
        self.ocr_tab.grid_columnconfigure(0, weight=1)
        self.ocr_tab.grid_rowconfigure(10, weight=1)
        self.tools_tab.grid_columnconfigure(0, weight=1)  # 配置新选项卡
        self.tools_tab.grid_rowconfigure(10, weight=1)

        # 在截图工具选项卡中添加控件
        # 文件夹路径输入框
        self.folder_path_entry = ctk.CTkEntry(self.screenshot_tab, placeholder_text="请选择保存图片文件夹", width=260, justify="center")
        self.folder_path_entry.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")
        # 选择文件夹按钮
        self.choese_folder_button = ctk.CTkButton(self.screenshot_tab, text="保存目录", width=20, command=self.choose_folder)
        self.choese_folder_button.grid(row=0, column=2, padx=(5, 10), pady=(10, 5), sticky="w")

        # 图片名称输入框
        self.img_name = ctk.CTkEntry(self.screenshot_tab, placeholder_text="请选择加载的图片", width=260, justify="center")
        self.img_name.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="ew")
        # 读取图片按钮
        self.load_image_button = ctk.CTkButton(self.screenshot_tab, text="加载图片", width=20, command=self.load_image)
        self.load_image_button.grid(row=1, column=2, padx=(5, 10), pady=(5, 5), sticky="w")

        # 请输入保存图片名称
        self.save_name_entry = ctk.CTkEntry(self.screenshot_tab, placeholder_text="请输入保存图片的名字", width=260, justify="center")
        self.save_name_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="ew")
        # 保存按钮
        self.save_and_fmt_button = ctk.CTkButton(self.screenshot_tab, text="保存图片", width=20, command=self.save_img)
        self.save_and_fmt_button.grid(row=2, column=2, padx=(5, 10), pady=(5, 5), sticky="w")

        # 框选坐标显示框
        self.rect_info = ctk.CTkEntry(self.screenshot_tab, placeholder_text="矩形框坐标", width=260, justify="center")
        self.rect_info.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 5), sticky="ew")
        # 绑定回车键事件，当在坐标输入框按回车时显示矩形框
        self.rect_info.bind("<KeyRelease>", self.show_rectangle_from_entry)
        # 复制按钮
        self.copy_button = ctk.CTkButton(self.screenshot_tab, width=20, text="复制坐标", command=lambda: self.copy_to_clipboard(str(self.coordinates)))
        self.copy_button.grid(row=3, column=2, padx=(5, 10), pady=(5, 5), sticky="w")

        # log显示框（放在控制面板框架内，在选项卡下方）
        self.log_frame = ctk.CTkFrame(self.control_frame)
        self.log_frame.grid(row=5, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        self.log_frame.grid_rowconfigure(0, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        # 添加标题标签
        self.log_title_label = ctk.CTkLabel(
            self.log_frame,
            text="操作日志",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.log_title_label.grid(row=0, column=0, padx=(10, 0), pady=(10, 0), sticky="w")

        # 添加清空日志按钮到标题栏右侧
        self.clear_log_button = ctk.CTkButton(
            self.log_frame,
            text="清除日志",
            width=60,
            height=20,
            command=self.clear_log
        )
        self.clear_log_button.grid(row=0, column=0, padx=(0, 10), pady=(10, 0), sticky="e")

        # 添加日志文本框
        self.log_box = ctk.CTkTextbox(
            self.log_frame,
            bg_color="#dadada",
            fg_color="#000000",
            text_color="#48BB31",
            width=120,
            height=480
        )
        self.log_box.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        
        # 在模板匹配选项卡中添加控件
        if MODULE_AVAILABLE:
            # 匹配方式选择标签和下拉框
            self.match_method_label = ctk.CTkLabel(self.template_tab, text="匹配方式:")
            self.match_method_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
            
            self.match_method_combo = ctk.CTkComboBox(
                self.template_tab,
                values=["图片匹配", "RuleImage匹配"],
                width=200,
                command=self.on_match_method_change
            )
            self.match_method_combo.set("RuleImage匹配")  # 默认选择
            self.match_method_combo.grid(row=0, column=1, padx=5, pady=5, sticky="e")
            
            # 模板路径显示 (用于图片匹配)
            self.template_path_label = ctk.CTkLabel(self.template_tab, text="未选择模板")
            self.template_path_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
            self.template_path_label.grid_remove()  # 默认隐藏
            # 选择模板按钮 (用于图片匹配)
            self.select_template_button = ctk.CTkButton(self.template_tab, text="选择模板", width=20, command=self.select_template)
            self.select_template_button.grid(row=1, column=1, padx=5, pady=10, sticky="e")
            self.select_template_button.grid_remove()  # 默认隐藏
            
            # RuleImage参数输入框 (用于RuleImage匹配)
            self.ruleimage_param_entry = ctk.CTkEntry(self.template_tab, placeholder_text="请输入RuleImage参数", width=260)
            self.ruleimage_param_entry.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

            # 阈值显示
            self.threshold_label = ctk.CTkLabel(self.template_tab, text="匹配阈值: 0.80")
            self.threshold_label.grid(row=3, column=0, padx=10, pady=10, sticky="w")
            # 阈值滑块
            self.threshold_slider = ctk.CTkSlider(self.template_tab, from_=0.1, to=1.0, number_of_steps=90, command=self.update_threshold_label)
            self.threshold_slider.set(0.8)
            self.threshold_slider.grid(row=3, column=1, padx=10, pady=10, sticky="ew")
            
            # 模板匹配按钮
            self.template_match_button = ctk.CTkButton(self.template_tab, text="模板匹配", width=30, command=self.perform_template_match)
            self.template_match_button.grid(row=4, column=1, padx=5, pady=10, sticky="e")

        # 在OCR工具选项卡中添加控件
        if MODULE_AVAILABLE:
            # OCR结果文本框
            self.ocr_result_textbox = ctk.CTkTextbox(self.ocr_tab, height=100, width=260)
            self.ocr_result_textbox.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
            self.ocr_result_textbox.insert("0.0", "OCR结果将显示在这里")

            # OCR按钮
            self.ocr_button = ctk.CTkButton(self.ocr_tab, text="执行OCR", width=20, command=self.perform_ocr)
            self.ocr_button.grid(row=1, column=0, columnspan=3, padx=10, pady=10, sticky="ew")

        # 在工具选项卡中添加控件
        # 添加检查画布尺寸按钮
        self.check_canvas_button = ctk.CTkButton(
            self.tools_tab,
            text="检查画布尺寸",
            width=260,
            command=self.check_canvas_size
        )
        self.check_canvas_button.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        # 如果蒙版生成器可用，添加相应按钮到工具选项卡
        if MASK_GENERATOR_AVAILABLE:
            # 蒙版生成器按钮
            self.mask_generator_button = ctk.CTkButton(
                self.tools_tab,
                text="蒙版生成器",
                width=260,
                command=self.open_mask_generator
            )
            self.mask_generator_button.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="ew")

        # 执行 assets_extract 按钮
        self.assets_extract_button = ctk.CTkButton(
            self.tools_tab,
            text="执行 assets_extract",
            width=260,
            command=self.run_assets_extract
        )
        self.assets_extract_button.grid(row=2, column=0, padx=10, pady=(5, 10), sticky="ew")

        # 当前选中模板路径
        self.current_template_path = None

        # 初始化保存路径输入框为默认保存路径
        self.folder_path_entry.insert(0, self.save_img_path)

        # 用于矩形拖动功能的变量
        self.is_dragging = False  # 是否正在拖动矩形
        self.drag_start_offset_x = 0  # 拖动起始点与矩形左上角的偏移
        self.drag_start_offset_y = 0  # 拖动起始点与矩形左上角的偏移
        # 用于新矩形绘制的变量
        self.is_drawing = False  # 是否正在绘制新矩形
        self.new_rect_start_x = 0  # 新矩形的起始点x坐标
        self.new_rect_start_y = 0  # 新矩形的起始点y坐标

        # 移除重复的画布尺寸设置

    def log_print(self, text):
        self.log_box.insert("end", f"{text}\n")
        self.log_box.update()
        self.log_box.see("end")

    def copy_to_clipboard(self, text):
        # 修改这里：改变复制到剪贴板的坐标格式
        x1, y1, x2, y2 = self.coordinates
        formatted_text = f"{x1-4},{y1-4},{x2-x1},{y2-y1}"
        # 彻底清理所有空白字符
        import re
        formatted_text = re.sub(r'\s+', '', formatted_text)

        # 使用更可靠的剪贴板方法
        pyperclip.copy(formatted_text)
        self.log_print(f"复制坐标 {formatted_text} 到剪贴板")

    def choose_folder(self):
        # 使用上次选择的路径或默认路径作为初始目录
        initial_dir = self.last_selected_folder or self.save_img_path
        folder_path = filedialog.askdirectory(initialdir=initial_dir)
        if folder_path:  # 如果选择了文件夹
            self.last_selected_folder = folder_path  # 记住选择的路径
            self.folder_path_entry.delete(0, "end")
            self.folder_path_entry.insert(0, folder_path)
            self.log_print(folder_path)

    def choose_image_file(self):
        """打开文件对话框选择PNG图片文件"""
        # 使用上次选择的路径或默认路径作为初始目录
        initial_dir = self.last_selected_image or self.screenshots_path
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="选择PNG图片",
            filetypes=(("PNG图片", "*.png"), ("所有文件", "*.*"))
        )
        if file_path:  # 如果选择了文件
            self.last_selected_image = os.path.dirname(file_path)  # 记住文件所在目录
        return file_path

    def load_image(self):
        """通过文件对话框加载PNG图片"""
        image_path = self.choose_image_file()
        if not image_path:  # 用户取消选择
            return

        self.log_print(f"加载图片: {os.path.basename(image_path)}")
        try:
            # 使用cv2读取图片
            self.np_image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)

            # 检查图片是否存在
            if self.np_image is None:
                self.log_print("无法读取图片文件")
                return

            # 检查图片尺寸
            if self.np_image.shape[1] != 1280 or self.np_image.shape[0] != 720:
                self.log_print(f"警告: 图片尺寸为 {self.np_image.shape[1]}x{self.np_image.shape[0]}，不是1280x720")

            # 转换为PIL Image并显示
            pil_image = Image.fromarray(cv2.cvtColor(self.np_image, cv2.COLOR_BGR2RGB))
            self.current_image = ImageTk.PhotoImage(pil_image)
            self.screen_canvas.create_image(4, 4, anchor="nw", image=self.current_image)

            # 设置图片名称为文件名（不含扩展名）
            img_name = os.path.splitext(os.path.basename(image_path))[0]
            self.img_name.delete(0, "end")
            self.img_name.insert(0, img_name)

            # 设置默认保存名称为加载图片名_1
            self.save_name_entry.delete(0, "end")
            self.save_name_entry.insert(0, f"{img_name}_1")

            # 自动填充文件夹路径为默认保存路径
            self.folder_path_entry.delete(0, "end")
            self.folder_path_entry.insert(0, self.save_img_path)

            # 重新绘制矩形框（如果存在）
            if self.rect["x1"] != self.rect["x2"] and self.rect["y1"] != self.rect["y2"]:
                self.draw_rectangle()

        except Exception as e:
            self.log_print(f"加载图片时出错: {e}")

    @property
    def coordinates(self):
        x1, y1, x2, y2 = self.rect.values()
        return x1, y1, x2, y2

    @property
    def name(self):
        return self.img_name.get()

    @property
    def file_path(self):
        base_path = self.folder_path_entry.get()
        img_name = self.name
        # 检查文件名是否合法
        if not img_name or not img_name.strip():
            self.log_print("图片名称不能为空")
            return
        # if not re.match(r"^[\w\-. ]+$", img_name):
        #     self.log_print("图片名称含有非法字符")
        #     return

        # 检查目录是否存在
        if not os.path.exists(base_path):
            self.log_print("保存路径不存在")
            return
        timestamp = datetime.now().strftime("%H%M%S")
        path = os.path.relpath(base_path, start=os.curdir) + "/" + img_name + f"_{timestamp}.png"  # 保存路径x
        path = path.replace("\\", "/")  # 路径格式化

        return path

    def save_img(self):

        # 检查是否已加载图片
        if self.np_image is None:
            self.log_print("请先加载图片")
            return

        # 检查是否已选择有效区域
        x1, y1, x2, y2 = self.coordinates
        if not (x1 != x2 and y1 != y2):  # 检查是否已选择区域
            self.log_print("请先选择要保存的区域")
            return

        # 获取保存名称输入框的内容作为文件名
        save_name = self.save_name_entry.get().strip()

        # 如果输入框为空，使用加载的图片名称作为基础名称
        if not save_name:
            base_name = self.name.strip()
            if base_name:
                save_name = f"{base_name}_1"
            else:
                self.log_print("保存图片的名字不能为空")
                return

        path = os.path.join(self.folder_path_entry.get(), f"{save_name}.png")

        # 检查文件是否已存在
        if os.path.exists(path):
            # 弹窗提示用户文件已存在，提供三个选项
            # self.withdraw()  # 隐藏主窗口，使对话框成为模态
            result = messagebox.askyesno(
                "文件已存在",
                f"文件 {save_name}.png 已存在，是否要覆盖该文件？\n\n '是' 覆盖文件\n '否' 取消保存"
            )
            # self.deiconify()  # 恢复主窗口

            if not result:  # 用户选择否，取消保存
                self.log_print("取消保存操作")
                return
            else:  # 用户选择是，覆盖文件
                self.log_print(f"将覆盖文件: {save_name}.png")

        if self.np_image is not None and any(self.rect.values()):  # 确保 np_image 和矩形框有效
            x1, y1, x2, y2 = self.coordinates
            # 检查裁剪框的有效性
            if not (0 <= x1 < x2 <= self.np_image.shape[1] and 0 <= y1 < y2 <= self.np_image.shape[0]):
                self.log_print("裁剪框的坐标无效")
                return
            try:
                cropped_image = self.np_image[y1 - 4 : y2 - 4, x1 - 4 : x2 - 4]
                cv2.imencode(".png", cropped_image)[1].tofile(path)
                self.log_print(f"{save_name}.png 保存成功")
                # 新增：保存图片信息到 image.json
                self.save_image_info(save_name, path, x1, y1, x2, y2)
            except Exception as e:
                self.log_print(f"保存图像时出错: {e}")

    def save_image_info(self, save_name, path, x1, y1, x2, y2):
        """保存图片信息到 image.json"""
        json_file_path = os.path.join(self.folder_path_entry.get(), "image.json")
        image_data = {
            "itemName": save_name,
            "imageName": f"{save_name}.png",
            "roiFront": f"{x1-4},{y1-4},{x2-x1},{y2-y1}",
            "roiBack":  f"{x1-4},{y1-4},{x2-x1},{y2-y1}",
            "method": "Template matching",
            "threshold": 0.8,
            "description": save_name
        }

        formatted_json = json.dumps(image_data, ensure_ascii=False, indent=2)
        self.log_print(formatted_json)

        roi = x1-4, y1-4, x2-x1, y2-y1
        self.log_print(f"rule_image = RuleImage(roi_front={roi}, roi_back={roi}, threshold=0.8, method=\"Template matching\", file=\"{self.folder_path_entry.get()}\\{save_name}.png\")")

        # 检查文件是否存在
        if os.path.exists(json_file_path):
            # 读取现有内容
            with open(json_file_path, 'r', encoding='utf-8') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        # 检查是否已存在相同的 itemName
        item_exists = False
        for item in data:
            if item["itemName"] == save_name:
                # 更新现有条目
                item.update(image_data)
                item_exists = True
                break

        # 如果不存在，则追加新数据
        if not item_exists:
            data.append(image_data)

        # 写回文件
        with open(json_file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=4)
            self.log_print(f"图片信息已保存到: {json_file_path}")

    def format_img(self, fmt_type):
        x1, y1, x2, y2 = self.coordinates
        match fmt_type:
            case "image":
                img_info = f"{self.name}=['{self.file_path}', [{x1-4}, {y1-4}, {x2-4}, {y2-4}], '{self.name}']"
            case "page":
                img_info = f"{self.name}=Page('{self.name}',['{self.file_path}', [{x1-4}, {y1-4}, {x2-4}, {y2-4}], '{self.name}'])"
            case "coor":
                img_info = f"{self.name}=({x1-4}, {y1-4}, {x2-4}, {y2-4})"
        return img_info
        pass

    def write_to_file(self, save_type):
        try:
            self._img_info = self.format_img(save_type)
            self.log_print(self._img_info)
            if self._img_info:
                if not os.path.exists(os.path.join(self.folder_path_entry.get(), "img_info_auto_create.py")):
                    with open(os.path.join(self.folder_path_entry.get(), "img_info_auto_create.py"), "w") as file:
                        file.write(f"# this file is auto created by devtool at {datetime.now()}\n\n")  # 写入内容
                        self.log_print("创建文件成功")

                with open(os.path.join(self.folder_path_entry.get(), "img_info_auto_create.py"), "a") as f:
                    f.write(str(self._img_info) + "\n")  # 写入内容
                    self.log_print("写入文件成功")
            else:
                self.log_print("没有图像信息或图像名称")
        except Exception as e:
            self.log_print(f"写入文件时出错: {e}")

    def in_canvas(self, event):
        self.mouse_is_in_canvas = True
        # self.log_print("鼠标进入画布")

    def out_canvas(self, event):
        self.mouse_is_in_canvas = False
        # self.log_print("鼠标离开画布")

    def on_click(self, event):
        if self.mouse_is_in_canvas:
            # 检查是否点击在现有矩形内
            x1, y1, x2, y2 = self.rect["x1"], self.rect["y1"], self.rect["x2"], self.rect["y2"]
            # 确保矩形有效（有面积）
            if x1 != x2 and y1 != y2:
                # 标准化矩形坐标（处理从右下到左上的绘制情况）
                left = min(x1, x2)
                right = max(x1, x2)
                top = min(y1, y2)
                bottom = max(y1, y2)
                
                # 判断点击是否在矩形内部
                if left <= event.x <= right and top <= event.y <= bottom:
                    self.is_dragging = True
                    self.drag_start_offset_x = event.x - x1
                    self.drag_start_offset_y = event.y - y1
                    return
            
            # 如果不在矩形内，则准备开始新的绘制（但不立即开始）
            self.is_dragging = False
            self.is_drawing = False
            # 注意：这里不立即改变矩形坐标，只记录点击位置用于后续可能的绘制
            self.new_rect_start_x = event.x
            self.new_rect_start_y = event.y

    def on_move(self, event):
        if self.mouse_is_in_canvas:
            if self.is_dragging:
                # 拖动矩形 - 平移整个矩形
                # 计算新位置
                new_x1 = event.x - self.drag_start_offset_x
                new_y1 = event.y - self.drag_start_offset_y
                
                # 保持矩形大小不变
                width = self.rect["x2"] - self.rect["x1"]
                height = self.rect["y2"] - self.rect["y1"]
                
                # 更新矩形坐标
                self.rect["x1"] = new_x1
                self.rect["y1"] = new_y1
                self.rect["x2"] = new_x1 + width
                self.rect["y2"] = new_y1 + height
                
                self.draw_rectangle()
            else:
                # 准备绘制新矩形或正在绘制新矩形
                if not self.is_drawing:
                    # 开始绘制新矩形
                    self.is_drawing = True
                    # 设置矩形的起始点和结束点
                    self.rect["x1"] = self.new_rect_start_x
                    self.rect["y1"] = self.new_rect_start_y
                    self.rect["x2"] = event.x
                    self.rect["y2"] = event.y
                else:
                    # 更新矩形的结束点
                    self.rect["x2"] = event.x
                    self.rect["y2"] = event.y
                self.draw_rectangle()

    def on_release(self, event):
        if self.mouse_is_in_canvas:
            if self.is_dragging:
                # 完成拖动
                self.is_dragging = False
                # 更新坐标显示
                x1, y1, x2, y2 = self.coordinates
                self.log_print(f"矩形框坐标：{x1-4},{y1-4},{x2-x1},{y2-y1}")
                self.dyn_creat_info()
            else:
                # 处理新矩形绘制
                if self.is_drawing:
                    # 完成新矩形绘制
                    self.rect["x2"] = event.x
                    self.rect["y2"] = event.y
                    # 检查是否实际拉出了矩形框（即起点和终点不同）
                    if self.rect["x1"] != self.rect["x2"] and self.rect["y1"] != self.rect["y2"]:
                        self.draw_rectangle()
                        # 修改这里：改变日志中坐标的显示格式
                        x1, y1, x2, y2 = self.coordinates
                        self.log_print(f"矩形框坐标：{x1-4},{y1-4},{x2-x1},{y2-y1}")
                        self.dyn_creat_info()
                # 重置绘制状态
                self.is_drawing = False
                self.new_rect_start_x = 0
                self.new_rect_start_y = 0

    def dyn_creat_info(self, *args, **kwargs):
        # 修改这里：改变矩形框坐标显示框中的格式
        x1, y1, x2, y2 = self.coordinates
        self.rect_info.delete(0, "end")
        self.rect_info.insert(0, f"{x1-4},{y1-4},{x2-x1},{y2-y1}")
        # self.img_info.delete(0, "end")
        # self.img_info.insert(0, f"{self.format_img('image')}")
        # self.page_info.delete(0, "end")
        # self.page_info.insert(0, f"{self.format_img('page')}")
        # self.click_info.delete(0, "end")
        # self.click_info.insert(0, f"{self.format_img('coor')}")

    def draw_rectangle(self):
        self.screen_canvas.delete("rect")
        self.screen_canvas.create_rectangle(self.rect["x1"], self.rect["y1"], self.rect["x2"], self.rect["y2"], outline="red", tags="rect")

    def show_rectangle_from_entry(self, event=None):
        """从坐标输入框获取坐标并在画布上显示矩形框"""
        coord_text = self.rect_info.get().strip()
        # 去掉所有空格，并将中文逗号替换为英文逗号
        coord_text = coord_text.replace(" ", "").replace("，", ",")
        if not coord_text:
            return

        try:
            # 解析坐标格式 x,y,w,h
            coords = [float(x.strip()) for x in coord_text.split(',')]
            if len(coords) == 2:
                coords.append(10)
                coords.append(10)
            if len(coords) != 4:
                return  # 不完整的坐标不处理

            x, y, w, h = coords
            # 转换为画布坐标 (加上偏移量4)
            x1 = int(x) + 4
            y1 = int(y) + 4
            x2 = x1 + int(w)
            y2 = y1 + int(h)

            # 检查坐标是否在图像范围内
            if self.np_image is not None:
                if not (0 <= x1 < x2 <= self.np_image.shape[1]+8 and 0 <= y1 < y2 <= self.np_image.shape[0]+8):
                    # 坐标超出范围时不绘制，但不清除现有矩形
                    return

            # 更新矩形坐标
            self.rect["x1"] = x1
            self.rect["y1"] = y1
            self.rect["x2"] = x2
            self.rect["y2"] = y2

            # 绘制矩形
            self.draw_rectangle()

        except ValueError:
            # 输入非数字时不处理
            pass
        except Exception:
            # 其他异常也不处理
            pass

    # 新增功能：OCR识别
    def perform_ocr(self):
        """执行OCR识别"""
        if not MODULE_AVAILABLE:
            self.log_print("项目模块不可用，无法执行OCR")
            return
            
        if self.np_image is None:
            self.log_print("请先加载图片")
            return

        if not self.is_rect_valid():
            self.log_print("请先选择有效区域")
            return

        try:
            # 获取选区坐标
            x1, y1, x2, y2 = self.coordinates
            # 转换为图片坐标系
            x1, y1, x2, y2 = x1 - 4, y1 - 4, x2 - 4, y2 - 4
            
            # 确保坐标有效
            x1, x2 = sorted([x1, x2])
            y1, y2 = sorted([y1, y2])
            
            if x1 < 0 or y1 < 0 or x2 > self.np_image.shape[1] or y2 > self.np_image.shape[0]:
                self.log_print("选区超出图片范围")
                return
                
            # 创建RuleOcr对象
            ocr_rule = RuleOcr(roi=(x1, y1, x2-x1, y2-y1), area=(x1, y1, x2-x1, y2-y1), mode="Single", method="Default", keyword="", name="devtool_ocr")

            # 转换图片格式
            rgb_image = cv2.cvtColor(self.np_image, cv2.COLOR_BGR2RGB)
            
            # 执行OCR
            ocr_result = ocr_rule.detect_and_ocr(rgb_image)
            
            # 显示结果
            if ocr_result:
                self.ocr_result_textbox.delete("0.0", "end")
                if isinstance(ocr_result, list):
                    for result in ocr_result:
                        self.ocr_result_textbox.insert("end", f"{result}\n")
                else:
                    self.ocr_result_textbox.insert("end", str(ocr_result))
                self.log_print(f"OCR识别完成: {ocr_result}")
            else:
                self.ocr_result_textbox.delete("0.0", "end")
                self.ocr_result_textbox.insert("0.0", "未识别到文本")
                self.log_print("OCR未识别到文本")
                
        except Exception as e:
            self.log_print(f"OCR执行出错: {str(e)}")

    # 新增功能：选择模板
    def select_template(self):
        """选择模板图片"""
        if not MODULE_AVAILABLE:
            self.log_print("项目模块不可用")
            return
            
        template_path = filedialog.askopenfilename(
            title="选择模板图片",
            filetypes=(("PNG图片", "*.png"), ("所有文件", "*.*"))
        )
        
        if template_path:
            self.current_template_path = template_path
            # 显示文件名
            filename = os.path.basename(template_path)
            self.template_path_label.configure(text=filename)
            self.log_print(f"已选择模板: {filename}")

    # 新增功能：匹配方式改变处理
    def on_match_method_change(self, choice):
        """处理匹配方式选择改变"""
        if choice == "图片匹配":
            # 显示模板选择控件
            self.template_path_label.grid()
            self.select_template_button.grid()
            # 隐藏RuleImage参数输入框
            self.ruleimage_param_entry.grid_remove()
        else:  # RuleImage匹配
            # 隐藏模板选择控件
            self.template_path_label.grid_remove()
            self.select_template_button.grid_remove()
            # 显示RuleImage参数输入框
            self.ruleimage_param_entry.grid()
            
        self.log_print(f"匹配方式已更改为: {choice}")

    # 新增功能：模板匹配
    def perform_template_match(self):
        """执行模板匹配"""
        if not MODULE_AVAILABLE:
            self.log_print("项目模块不可用，无法执行模板匹配")
            return
            
        if self.np_image is None:
            self.log_print("请先加载图片")
            return

        # 获取当前选择的匹配方式
        match_method = self.match_method_combo.get()
        
        if match_method == "图片匹配":
            if not self.current_template_path:
                self.log_print("请先选择模板图片")
                return

            if not self.is_rect_valid():
                self.log_print("请先选择有效区域")
                return
            try:
                # 获取选区坐标
                x1, y1, x2, y2 = self.coordinates
                # 转换为图片坐标系
                x1, y1, x2, y2 = x1 - 4, y1 - 4, x2 - 4, y2 - 4

                # 确保坐标有效
                x1, x2 = sorted([x1, x2])
                y1, y2 = sorted([y1, y2])

                if x1 < 0 or y1 < 0 or x2 > self.np_image.shape[1] or y2 > self.np_image.shape[0]:
                    self.log_print("选区超出图片范围")
                    return

                # 获取当前阈值
                threshold = self.threshold_slider.get()

                # 执行图片匹配逻辑
                self._perform_image_match(x1, y1, x2, y2, threshold)

            except Exception as e:
                self.log_print(f"模板匹配执行出错: {str(e)}")

        else:
            # 执行RuleImage匹配逻辑
            self._perform_ruleimage_match()

    def _perform_image_match(self, x1, y1, x2, y2, threshold):
        """执行图片匹配"""
        # 创建RuleImage对象
        template_rule = RuleImage(
            roi_front=(x1, y1, x2-x1, y2-y1),
            roi_back=(x1, y1, x2-x1, y2-y1),
            threshold=threshold,
            method="Template matching",
            file=self.current_template_path
        )
        print(f"Template matching: {template_rule.roi_front}")
        self._perform_match(template_rule)


    def _perform_ruleimage_match(self):
        """执行RuleImage匹配"""
        try:
            # 获取RuleImage参数
            ruleimage_param = self.ruleimage_param_entry.get().strip()
            self.log_print(f"使用RuleImage参数: {ruleimage_param}")
            print(f"RuleImage: {ruleimage_param}")

            # 解析字符串参数并创建RuleImage对象
            # 假设输入格式为: RuleImage(roi_front=(176,148,144,108), roi_back=(128,142,902,449), threshold=0.8, method="Template matching", file="./tasks/RichMan/mall/special/special_sp_buy_low.png")
            if "RuleImage" in ruleimage_param and ruleimage_param.endswith(")"):
                # 提取参数部分
                params_str = ruleimage_param[10:-1]  # 去掉"RuleImage("和最后的")"

                # 解析参数（这里需要根据实际格式进行解析）
                # 简化处理，您可以根据实际需要进行更复杂的解析
                # 例如，可以使用正则表达式或eval（注意安全性）
                # 这里假设参数格式是固定的

                # 提取roi_front
                roi_front_match = re.search(r'roi_front=\(([^)]+)\)', params_str)
                if not roi_front_match:
                    self.log_print("roi_front参数格式不正确")
                    return  # 匹配失败，直接返回
                roi_front = tuple(map(int, roi_front_match.group(1).split(',')))

                # 提取roi_back
                roi_back_match = re.search(r'roi_back=\(([^)]+)\)', params_str)
                if not roi_back_match:
                    self.log_print("roi_back参数格式不正确")
                    return  # 匹配失败，直接返回
                roi_back = tuple(map(int, roi_back_match.group(1).split(',')))

                # 提取threshold
                threshold_match = re.search(r'threshold=([\d.]+)', params_str)
                if not threshold_match:
                    self.log_print("threshold参数格式不正确")
                    return  # 匹配失败，直接返回
                threshold = float(threshold_match.group(1))

                # 提取method
                method_match = re.search(r'method=([\'"])([^\'"]+)\1', params_str)
                if not method_match:
                    self.log_print("method参数格式不正确")
                    return  # 匹配失败，直接返回
                method = method_match.group(2)

                # 提取file
                file_match = re.search(r'file=([\'"])([^\'"]+)\1', params_str)
                if not file_match:
                    self.log_print("file参数格式不正确")
                    return  # 匹配失败，直接返回
                file = file_match.group(2)

                # 创建RuleImage对象
                template_rule = RuleImage(
                    roi_front=roi_front,
                    roi_back=roi_back,
                    threshold=threshold,
                    method=method,
                    file=file
                )

                self._perform_match(template_rule)
            else:
                self.log_print("RuleImage参数格式不正确")

        except Exception as e:
            self.log_print(f"RuleImage参数解析出错: {str(e)}")

    def _perform_match(self, template_rule):
        try:
            print(f"RuleImage: {template_rule}")
            # 转换图片格式
            rgb_image = cv2.cvtColor(self.np_image, cv2.COLOR_BGR2RGB)

            # 执行模板匹配
            match_result = template_rule.match(rgb_image)

            # 显示结果
            if match_result:
                # 在画布上绘制匹配结果
                self.screen_canvas.delete("match_result")
                roi = template_rule.roi_front
                # 转换回画布坐标系
                canvas_x1, canvas_y1 = roi[0] + 4, roi[1] + 4
                canvas_x2, canvas_y2 = roi[2], roi[3]
                self.screen_canvas.create_rectangle(
                    canvas_x1, canvas_y1, canvas_x1 + canvas_x2, canvas_y1 + canvas_y2,
                    outline="green", width=1, tags="match_result"  # 使用不同颜色区分
                )
                self.log_print(f"RuleImage匹配成功: {roi}")
            else:
                self.screen_canvas.delete("match_result")
                self.log_print("RuleImage匹配失败")
        except Exception as e:
            self.log_print(f"RuleImage匹配执行出错: {str(e)}")

    def open_mask_generator(self):
        """打开蒙版生成器"""
        try:
            # 构建命令行参数
            python_executable = r"F:\Python3.10\VENV\Scripts\pythonw.exe"
            script_path = r"D:\OnmyojiAutoScript\ljxun\mask_generator.py"

            # 启动子进程
            subprocess.Popen([python_executable, script_path])

        except Exception as e:
            self.log_print(f"启动蒙版生成器时出错: {str(e)}")

    def run_assets_extract(self):
        """生成 assets"""
        try:
            # 构建命令行参数
            python_executable = r"F:\Python3.10\VENV\Scripts\pythonw.exe"
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets_extract.py")
            self.log_print(script_path)

            # 启动子进程
            subprocess.Popen([python_executable, script_path])
            self.log_print("执行 assets_extract 成功")

        except Exception as e:
            self.log_print(f"执行 assets_extract 出错: {str(e)}")

    def check_canvas_size(self):
        """检查画布实际尺寸"""
        canvas_width = self.screen_canvas.winfo_width()
        canvas_height = self.screen_canvas.winfo_height()
        requested_width = self.screen_canvas.cget("width")
        requested_height = self.screen_canvas.cget("height")
        self.log_print(f"画布请求尺寸: {requested_width}x{requested_height}")
        self.log_print(f"画布实际尺寸: {canvas_width}x{canvas_height}")
        # 同时检查Canvas的配置
        self.log_print(f"Canvas配置: width={self.screen_canvas['width']}, height={self.screen_canvas['height']}")
        # 检查Canvas的边界框
        bbox = self.screen_canvas.bbox("all")
        if bbox:
            self.log_print(f"Canvas内容边界: {bbox}")
        else:
            self.log_print("Canvas中没有内容")
        
        # 检查父容器尺寸
        frame_width = self.canvas_frame.winfo_width()
        frame_height = self.canvas_frame.winfo_height()
        self.log_print(f"父容器尺寸: {frame_width}x{frame_height}")

    # 辅助方法：检查矩形是否有效
    def is_rect_valid(self):
        """检查当前选择的矩形是否有效"""
        x1, y1, x2, y2 = self.coordinates
        return (x1 != x2 and y1 != y2)

    # 新增功能：更新阈值标签
    def update_threshold_label(self, value):
        """更新阈值标签显示"""
        self.threshold_label.configure(text=f"匹配阈值: {float(value):.2f}")

    def clear_log(self):
        """清空日志框内容"""
        self.log_box.delete("0.0", "end")


if __name__ == "__main__":
    app = DevTool()
    app.mainloop()
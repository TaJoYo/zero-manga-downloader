#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
零漫画下载器 - Fluent UI
"""

import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QMessageBox, QSpinBox, QSlider, QListWidget, 
    QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from qfluentwidgets import (
    FluentWindow, FluentIcon,
    LineEdit, PushButton, ProgressBar, TextEdit,
    SimpleCardWidget, InfoBar, InfoBarPosition,
    ScrollArea
)
from qfluentwidgets import setTheme, Theme, setThemeColor

from manga_parser import MangaParser
from downloader import MangaDownloader
from config_manager import ConfigManager
from history_manager import HistoryManager


class DownloadThread(QThread):
    """下载线程"""
    
    progress_signal = pyqtSignal(str, str, str)
    chapter_signal = pyqtSignal(str, int, int, str, dict)
    finished_signal = pyqtSignal(dict)
    
    def __init__(self, downloader, manga_info, chapters, save_dir):
        super().__init__()
        self.downloader = downloader
        self.manga_info = manga_info
        self.chapters = chapters
        self.save_dir = save_dir
    
    def run(self):
        """运行下载"""
        def progress_callback(status, url, path, error=''):
            self.progress_signal.emit(status, url, error)
        
        def chapter_callback(status, current, total, name, stats=None):
            self.chapter_signal.emit(status, current, total, name, stats or {})
        
        stats = self.downloader.download_manga(
            self.manga_info,
            self.chapters,
            self.save_dir,
            progress_callback,
            chapter_callback
        )
        
        self.finished_signal.emit(stats)


class MangaDownloaderWindow(FluentWindow):
    """主窗口 - Fluent风格"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化管理器
        self.config = ConfigManager()
        self.history = HistoryManager(max_records=self.config.get_max_history_records())
        self.parser = MangaParser()
        self.downloader = None
        self.download_thread = None
        
        # 当前漫画信息
        self.current_manga = None
        
        # 应用主题
        self.apply_theme()
        
        # 设置字体
        self.apply_font()
        
        self.init_ui()
        self.load_config()
    
    def apply_theme(self):
        """应用主题 - 始终使用明亮模式"""
        # 应用 Fluent 明亮主题
        setTheme(Theme.LIGHT)
        
        # 设置强调色
        setThemeColor('#2196F3')
        
        # 延迟更新样式表，确保 Fluent 主题已完全应用
        QApplication.instance().processEvents()
        self.apply_font()
        
        # 强制刷新整个窗口以应用主题
        self.repaint()
        QApplication.instance().processEvents()
    
    def apply_font(self):
        """应用字体大小到所有控件"""
        font_size = self.config.get_font_size()
        
        # 创建主字体
        main_font = QFont("Microsoft YaHei, Segoe UI, 宋体")
        main_font.setPointSize(font_size)
        main_font.setStyleStrategy(QFont.PreferAntialias)
        
        # 应用全局字体
        QApplication.instance().setFont(main_font)
        
        # 计算动态尺寸
        btn_height = max(36, font_size + 16)          # 按钮高度 - 更紧凑
        btn_width_2char = max(80, font_size * 8)      # 两字按钮（全选、解析）
        btn_width_3char = max(120, font_size * 15)    # 三字按钮（全不选）- 更大
        input_height = max(36, font_size + 16)        # 输入框高度 - 与按钮对齐
        large_btn_width = max(100, font_size * 10)
        
        # 根据主题选择颜色（暗黑模式 vs 明亮模式）
        theme_setting = self.config.get_theme()
        is_dark = True if theme_setting == 'dark' else False
        
        if is_dark:
            # 深色模式颜色
            border_color = "#3C3C3C"
            slider_handle = "#2196F3"
            slider_handle_hover = "#42A5F5"
        else:
            # 明亮模式颜色
            border_color = "#E0E0E0"
            slider_handle = "#2196F3"
            slider_handle_hover = "#1976D2"
        
        # 全局样式表 - 仅设置尺寸，让 Fluent 控制所有颜色/背景/字体颜色
        title_size = max(13, font_size + 3)
        stylesheet = f"""
            /* 输入框大小 */
            QLineEdit {{ padding: 4px; min-height: {input_height}px; }}
            QSpinBox {{ padding: 2px; min-height: {input_height}px; }}
            QComboBox {{ padding: 2px; min-height: {input_height}px; }}
            QPushButton {{ padding: 6px 12px; min-height: {btn_height}px; }}
            
            /* 标题样式 */
            #dl_title, #ui_title, #acc_title, #hist_title {{ 
                font-weight: bold;
                font-size: {title_size}pt;
            }}
            
            /* 滑块样式 */
            QSlider::groove:horizontal {{
                background-color: #E8E8E8;
                height: 6px;
                margin: 4px 0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background-color: {slider_handle};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
                border: none;
            }}
            QSlider::handle:horizontal:hover {{
                background-color: {slider_handle_hover};
                width: 18px;
                margin: -6px 0;
            }}
            QSlider::sub-page:horizontal {{
                background-color: {slider_handle};
                border-radius: 3px;
            }}
            QSlider {{ min-height: {max(28, font_size + 10)}px; }}
        """
        
        QApplication.instance().setStyleSheet(stylesheet)
        
        # 动态更新控件颜色 - 根据当前主题
        self._update_dynamic_colors(is_dark)
        
        # 直接更新所有控件的尺寸（确保覆盖样式表）
        # 首页按钮
        if hasattr(self, 'url_history_btn'):
            self.url_history_btn.setMinimumHeight(input_height)
            self.url_history_btn.setMinimumWidth(large_btn_width)
        if hasattr(self, 'parse_btn'):
            self.parse_btn.setMinimumHeight(input_height)
            self.parse_btn.setMinimumWidth(btn_width_2char)
        if hasattr(self, 'url_input'):
            self.url_input.setMinimumHeight(input_height)
        
        if hasattr(self, 'select_all_btn'):
            self.select_all_btn.setMinimumHeight(btn_height)
            self.select_all_btn.setMinimumWidth(btn_width_2char)
        if hasattr(self, 'deselect_all_btn'):
            self.deselect_all_btn.setMinimumHeight(btn_height)
            self.deselect_all_btn.setMinimumWidth(btn_width_3char)  # 三字按钮用更大宽度
        
        # 设置页按钮和控件
        if hasattr(self, 'threads_slider'):
            self.threads_slider.setMinimumHeight(32)
        if hasattr(self, 'font_slider'):
            self.font_slider.setMinimumHeight(32)
    
    def _update_dynamic_colors(self, is_dark: bool):
        """根据主题动态更新硬编码颜色的控件"""
        # 选择颜色方案
        if is_dark:
            hint_color = "#AAAAAA"      # 深色模式：浅灰色提示
            label_color = "#CCCCCC"     # 深色模式：更浅的标签色
            warning_color = "#FFB74D"   # 深色模式：更亮的橙色
        else:
            hint_color = "#999"         # 明亮模式：深灰色提示
            label_color = "#666"        # 明亮模式：深灰色标签
            warning_color = "#FF9800"   # 明亮模式：橙色
        
        # 更新示例文本颜色
        if hasattr(self, 'example'):
            self.example.setStyleSheet(f'color: {hint_color};')
        
        # 更新状态标签颜色
        if hasattr(self, 'status_label'):
            self.status_label.setStyleSheet(f'color: {label_color};')
        
        # 更新提示按钮颜色
        if hasattr(self, 'note'):
            self.note.setStyleSheet(f'color: {warning_color}; font-size: 12px; margin-left: 130px;')

    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle('零漫画下载器')
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)
        
        # 隐藏返回按钮
        self.navigationInterface.setReturnButtonVisible(False)
        
        # 创建页面
        self.home_page = self.create_home_page()
        self.settings_page = self.create_settings_page()
        
        # 注册导航菜单
        self.addSubInterface(self.home_page, FluentIcon.HOME, '首页')
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, '设置')
    
    def create_home_page(self) -> QWidget:
        """创建主页 - 使用ScrollArea架构，与设置页保持一致"""
        page = QWidget()
        page.setObjectName('HomePage')
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 使用ScrollArea包含所有内容
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 10px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #D0D0D0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A0A0A0;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(30, 30, 30, 30)
        scroll_layout.setSpacing(20)
        
        # ===== URL输入区 =====
        url_card = SimpleCardWidget()
        url_layout = QVBoxLayout(url_card)
        url_layout.setContentsMargins(20, 20, 20, 20)
        url_layout.setSpacing(12)
        
        url_title = QLabel('漫画URL')
        url_title.setStyleSheet('font-weight: bold;')
        url_layout.addWidget(url_title)
        
        example = QLabel('例如: https://www.zerobywai.com/pc/manga_pc.php?kuid=7887')
        example.setStyleSheet('color: #999;')
        example.setWordWrap(True)
        url_layout.addWidget(example)
        
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.url_history_btn = PushButton('📋 历史')
        self.url_history_btn.setMinimumHeight(40)
        self.url_history_btn.clicked.connect(self.show_url_history)
        input_row.addWidget(self.url_history_btn)
        
        self.url_input = LineEdit()
        self.url_input.setPlaceholderText('输入漫画URL...')
        self.url_input.setMinimumHeight(40)
        input_row.addWidget(self.url_input)
        
        self.parse_btn = PushButton('解析')
        self.parse_btn.setMinimumHeight(40)
        self.parse_btn.clicked.connect(self.parse_url)
        input_row.addWidget(self.parse_btn)
        
        url_layout.addLayout(input_row)
        scroll_layout.addWidget(url_card)
        
        # ===== 信息显示区 =====
        info_card = SimpleCardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(16)
        
        # 标题行
        title_row = QHBoxLayout()
        title_row.setSpacing(20)
        title_label = QLabel('标题:')
        title_label.setMinimumWidth(100)
        title_label.setMaximumWidth(100)
        self.manga_title_label = QLabel('未解析')
        title_row.addWidget(title_label, 0)
        title_row.addWidget(self.manga_title_label, 1)
        info_layout.addLayout(title_row)
        
        # 章节数行
        chapters_row = QHBoxLayout()
        chapters_row.setSpacing(20)
        chapters_label = QLabel('章节数:')
        chapters_label.setMinimumWidth(100)
        chapters_label.setMaximumWidth(100)
        self.manga_chapters_label = QLabel('0')
        chapters_row.addWidget(chapters_label, 0)
        chapters_row.addWidget(self.manga_chapters_label, 1)
        info_layout.addLayout(chapters_row)
        
        scroll_layout.addWidget(info_card)
        
        # ===== 章节选择区 =====
        chapter_card = SimpleCardWidget()
        chapter_layout = QVBoxLayout(chapter_card)
        chapter_layout.setContentsMargins(20, 20, 20, 20)
        chapter_layout.setSpacing(12)
        
        chapter_title = QLabel('选择章节')
        chapter_title.setStyleSheet('font-weight: bold;')
        chapter_layout.addWidget(chapter_title)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.select_all_btn = PushButton('✓ 全选')
        self.select_all_btn.setMinimumHeight(40)
        self.select_all_btn.clicked.connect(lambda: self.set_chapter_selection(True))
        btn_row.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = PushButton('✗ 全不选')
        self.deselect_all_btn.setMinimumHeight(40)
        self.deselect_all_btn.clicked.connect(lambda: self.set_chapter_selection(False))
        btn_row.addWidget(self.deselect_all_btn)
        
        btn_row.addStretch()
        chapter_layout.addLayout(btn_row)
        
        self.chapter_list = QListWidget()
        self.chapter_list.setMinimumHeight(200)
        chapter_layout.addWidget(self.chapter_list)
        
        scroll_layout.addWidget(chapter_card)
        
        # ===== 下载控制区 =====
        control_card = SimpleCardWidget()
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(10)
        
        self.download_btn = PushButton('▶ 开始下载')
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setEnabled(False)
        self.download_btn.setMinimumHeight(40)
        control_layout.addWidget(self.download_btn)
        
        self.cancel_btn = PushButton('⏹ 取消')
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumHeight(40)
        control_layout.addWidget(self.cancel_btn)
        
        scroll_layout.addWidget(control_card)
        
        # ===== 进度显示区 =====
        progress_card = SimpleCardWidget()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(12)
        
        progress_title = QLabel('下载进度')
        progress_title.setStyleSheet('font-weight: bold;')
        progress_layout.addWidget(progress_title)
        
        self.progress_bar = ProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumHeight(32)
        self.progress_bar.setMinimumWidth(400)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel('就绪')
        self.status_label.setStyleSheet('color: #666;')
        progress_layout.addWidget(self.status_label)
        
        self.log_text = TextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        progress_layout.addWidget(self.log_text)
        
        scroll_layout.addWidget(progress_card)
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        return page
    
    def create_settings_page(self) -> QWidget:
        """创建设置页面 - 使用ScrollArea并固定标签宽度"""
        page = QWidget()
        page.setObjectName('SettingsPage')
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 使用ScrollArea包含所有内容
        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 10px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #D0D0D0;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #A0A0A0;
            }
        """)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(30, 30, 30, 30)
        scroll_layout.setSpacing(20)
        
        # ===== 下载设置 =====
        download_card = SimpleCardWidget()
        dl_layout = QVBoxLayout(download_card)
        dl_layout.setContentsMargins(20, 20, 20, 20)
        dl_layout.setSpacing(18)
        
        dl_title = QLabel('下载设置')
        dl_title.setObjectName('dl_title')
        dl_layout.addWidget(dl_title)
        
        # 线程数
        thread_row = self._create_setting_row('线程数:', 120)
        self.threads_slider = QSlider(Qt.Horizontal)
        self.threads_slider.setMinimum(1)
        self.threads_slider.setMaximum(50)
        self.threads_slider.setValue(15)
        self.threads_slider.setMinimumHeight(32)
        self.threads_value_label = QLabel('15')
        self.threads_value_label.setMinimumWidth(30)
        self.threads_slider.valueChanged.connect(
            lambda v: self.threads_value_label.setText(str(v))
        )
        thread_row.addWidget(self.threads_slider, 1)
        thread_row.addWidget(self.threads_value_label, 0)
        dl_layout.addLayout(thread_row)
        
        note = QLabel('⚠ 过多线程可能被封IP，建议5-20')
        note.setStyleSheet('color: #FF9800; font-size: 12px; margin-left: 130px;')
        dl_layout.addWidget(note)
        
        # 重试次数
        retry_row = self._create_setting_row('重试次数:', 120)
        self.retry_spin = QSpinBox()
        self.retry_spin.setMinimum(1)
        self.retry_spin.setMaximum(10)
        self.retry_spin.setValue(3)
        self.retry_spin.setMaximumWidth(100)
        self.retry_spin.setMinimumHeight(32)
        retry_row.addWidget(self.retry_spin, 0)
        retry_row.addStretch()
        dl_layout.addLayout(retry_row)
        
        # 重试延迟
        delay_row = self._create_setting_row('重试延迟:', 120)
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(60)
        self.delay_spin.setValue(2)
        self.delay_spin.setMaximumWidth(100)
        self.delay_spin.setMinimumHeight(32)
        delay_row.addWidget(self.delay_spin, 0)
        delay_row.addStretch()
        dl_layout.addLayout(delay_row)
        
        # 下载目录
        dir_row = self._create_setting_row('下载目录:', 120)
        self.download_dir_input = LineEdit()
        self.download_dir_input.setMinimumHeight(32)
        dir_row.addWidget(self.download_dir_input, 1)
        browse_btn = PushButton('浏览')
        browse_btn.setMaximumWidth(80)
        browse_btn.setMinimumHeight(32)
        browse_btn.clicked.connect(self.select_download_dir)
        dir_row.addWidget(browse_btn, 0)
        dl_layout.addLayout(dir_row)
        
        scroll_layout.addWidget(download_card)
        
        # ===== UI设置 =====
        ui_card = SimpleCardWidget()
        ui_layout = QVBoxLayout(ui_card)
        ui_layout.setContentsMargins(20, 20, 20, 20)
        ui_layout.setSpacing(18)
        
        ui_title = QLabel('界面设置')
        ui_title.setObjectName('ui_title')
        ui_layout.addWidget(ui_title)
        
        # 字体大小
        font_row = self._create_setting_row('字体大小:', 120)
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setMinimum(8)
        self.font_slider.setMaximum(16)
        self.font_slider.setValue(self.config.get_font_size())
        self.font_slider.setMaximumWidth(250)
        self.font_slider.setMinimumHeight(32)
        
        # 字体变化时实时应用
        def update_font_preview(value):
            self.config.set_font_size(value)
            self.apply_font()
        
        self.font_slider.valueChanged.connect(update_font_preview)
        font_row.addWidget(self.font_slider, 0)
        font_row.addStretch()
        ui_layout.addLayout(font_row)
        
        scroll_layout.addWidget(ui_card)
        
        # ===== 账户设置 =====
        account_card = SimpleCardWidget()
        acc_layout = QVBoxLayout(account_card)
        acc_layout.setContentsMargins(20, 20, 20, 20)
        acc_layout.setSpacing(18)
        
        acc_title = QLabel('账户设置（可选）')
        acc_title.setObjectName('acc_title')
        acc_layout.addWidget(acc_title)
        
        # 用户名
        username_row = self._create_setting_row('用户名:', 120)
        self.username_input = LineEdit()
        self.username_input.setPlaceholderText('用户名')
        self.username_input.setMinimumHeight(32)
        username_row.addWidget(self.username_input, 1)
        acc_layout.addLayout(username_row)
        
        # 密码
        password_row = self._create_setting_row('密码:', 120)
        self.password_input = LineEdit()
        self.password_input.setPlaceholderText('密码')
        self.password_input.setEchoMode(LineEdit.Password)
        self.password_input.setMinimumHeight(32)
        password_row.addWidget(self.password_input, 1)
        acc_layout.addLayout(password_row)
        
        scroll_layout.addWidget(account_card)
        
        # ===== 历史管理 =====
        history_card = SimpleCardWidget()
        hist_layout = QVBoxLayout(history_card)
        hist_layout.setContentsMargins(20, 20, 20, 20)
        hist_layout.setSpacing(18)
        
        hist_title = QLabel('历史记录')
        hist_title.setObjectName('hist_title')
        hist_layout.addWidget(hist_title)
        
        clear_btn = PushButton('🗑 清空历史')
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(self.clear_history)
        hist_layout.addWidget(clear_btn)
        
        scroll_layout.addWidget(history_card)
        
        scroll_layout.addStretch()
        
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)
        
        # ===== 保存按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(30, 15, 30, 15)
        save_btn = PushButton('💾 保存设置')
        save_btn.setMinimumHeight(45)
        save_btn.clicked.connect(self.save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(save_btn, 0)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)
        
        return page
    
    def _create_setting_row(self, label_text: str, label_width: int) -> QHBoxLayout:
        """创建设置行 - 标签固定宽度"""
        row = QHBoxLayout()
        row.setSpacing(15)
        label = QLabel(label_text)
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(label, 0)
        return row
    
    def log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def parse_url(self):
        """解析URL"""
        url = self.url_input.text().strip()
        
        if not url:
            self.show_info_bar('请输入漫画URL', '错误', InfoBarPosition.TOP)
            return
        
        self.log('⏳ 正在解析URL...')
        self.parse_btn.setEnabled(False)
        
        try:
            manga_info = self.parser.parse_manga_url(url)
            self.current_manga = manga_info
            
            self.manga_title_label.setText(manga_info['title'])
            self.manga_chapters_label.setText(str(manga_info['total_chapters']))
            
            self.chapter_list.clear()
            for chapter in manga_info['chapters']:
                item = QListWidgetItem(chapter['title'])
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.chapter_list.addItem(item)
            
            self.download_btn.setEnabled(True)
            self.log(f'✓ 解析成功！找到 {manga_info["total_chapters"]} 个章节')
            if manga_info.get('manga_id'):
                self.log(f'  漫画ID: {manga_info["manga_id"]}')
            
            if self.config.is_history_enabled():
                self.history.add_record(
                    url,
                    manga_info['title'],
                    manga_info['total_chapters'],
                    'parsed'
                )
        
        except Exception as e:
            self.log(f'✗ 解析失败: {str(e)}')
            self.show_info_bar(f'解析URL失败: {str(e)}', '错误', InfoBarPosition.TOP)
        
        finally:
            self.parse_btn.setEnabled(True)
    
    def set_chapter_selection(self, checked: bool):
        """设置章节选择状态"""
        state = Qt.Checked if checked else Qt.Unchecked
        for i in range(self.chapter_list.count()):
            self.chapter_list.item(i).setCheckState(state)
    
    def start_download(self):
        """开始下载"""
        if not self.current_manga:
            return
        
        selected_chapters = []
        for i in range(self.chapter_list.count()):
            if self.chapter_list.item(i).checkState() == Qt.Checked:
                selected_chapters.append(i)
        
        if not selected_chapters:
            self.show_info_bar('请至少选择一个章节', '警告', InfoBarPosition.TOP)
            return
        
        download_dir = self.config.get_download_dir()
        if not Path(download_dir).exists():
            Path(download_dir).mkdir(parents=True, exist_ok=True)
        
        self.downloader = MangaDownloader(
            threads=self.config.get_download_threads(),
            retries=self.config.get_retries(),
            retry_delay=self.config.get_retry_delay()
        )
        
        self.download_thread = DownloadThread(
            self.downloader,
            self.current_manga,
            selected_chapters,
            download_dir
        )
        
        self.download_thread.progress_signal.connect(self.on_download_progress)
        self.download_thread.chapter_signal.connect(self.on_chapter_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)
        
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.parse_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.log(f'\n▶ 开始下载 {len(selected_chapters)} 个章节...')
        self.download_thread.start()
    
    def cancel_download(self):
        """取消下载"""
        if self.downloader:
            self.downloader.cancel()
            self.log('⏹ 正在取消下载...')
    
    def on_download_progress(self, status: str, url: str, detail: str):
        """下载进度更新"""
        pass
    
    def on_chapter_progress(self, status: str, current: int, total: int,
                           name: str, stats: dict):
        """章节进度更新"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        
        if status == 'start':
            self.status_label.setText(f'正在下载: {name} ({current}/{total})')
            self.log(f'[{current}/{total}] ⬇ {name}')
        
        elif status == 'complete':
            success = stats.get('success', 0)
            failed = stats.get('failed', 0)
            skipped = stats.get('skipped', 0)
            self.log(f'[{current}/{total}] ✓ {name} - '
                    f'{success}成/{failed}失/{skipped}跳')
        
        elif status == 'failed':
            error_msg = stats.get('error', '未知错误')
            self.log(f'[{current}/{total}] ✗ {name} - {error_msg}')
    
    def on_download_finished(self, stats: dict):
        """下载完成"""
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.parse_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        
        success_chapters = stats.get('success_chapters', 0)
        total_chapters = stats.get('total_chapters', 0)
        success_images = stats.get('success_images', 0)
        failed_images = stats.get('failed_images', 0)
        
        self.log(f'\n✓✓✓ 下载完成！')
        self.log(f'  章节: {success_chapters}/{total_chapters}')
        self.log(f'  图片: {success_images}成/{failed_images}失')
        
        self.status_label.setText('✓ 下载完成')
        
        if self.config.is_history_enabled() and self.current_manga:
            status = 'completed' if success_chapters == total_chapters else 'partial'
            self.history.add_record(
                self.current_manga['url'],
                self.current_manga['title'],
                total_chapters,
                status
            )
        
        self.show_info_bar(
            f'成功: {success_chapters}/{total_chapters}  |  '
            f'图片: {success_images}成/{failed_images}失',
            '完成',
            InfoBarPosition.TOP
        )
    
    def show_url_history(self):
        """显示URL历史"""
        records = self.history.get_recent_records(10)
        if not records:
            self.show_info_bar('暂无历史记录', '提示', InfoBarPosition.TOP)
            return
        
        from PyQt5.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle('历史记录')
        dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout()
        list_widget = QListWidget()
        
        for record in records:
            item = QListWidgetItem(f"{record['title']} ({record['chapters_count']}章)")
            item.setData(Qt.UserRole, record['url'])
            list_widget.addItem(item)
        
        list_widget.itemDoubleClicked.connect(
            lambda item: self.load_history_item(item.data(Qt.UserRole), dialog)
        )
        
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def load_history_item(self, url: str, dialog):
        """加载历史记录项"""
        self.url_input.setText(url)
        dialog.close()
    
    def select_download_dir(self):
        """选择下载目录"""
        directory = QFileDialog.getExistingDirectory(
            self,
            '选择下载目录',
            self.download_dir_input.text()
        )
        
        if directory:
            self.download_dir_input.setText(directory)
    
    def save_settings(self):
        """保存设置"""
        self.config.set_username(self.username_input.text())
        self.config.set_password(self.password_input.text())
        self.config.set_download_threads(self.threads_slider.value())
        self.config.set_retries(self.retry_spin.value())
        self.config.set_retry_delay(self.delay_spin.value())
        self.config.set_download_dir(self.download_dir_input.text())
        
        # 字体大小已在滑块变化时实时保存
        self.show_info_bar('设置已保存', '成功', InfoBarPosition.TOP)
    
    def load_config(self):
        """加载配置"""
        self.username_input.setText(self.config.get_username())
        self.password_input.setText(self.config.get_password())
        self.threads_slider.setValue(self.config.get_download_threads())
        self.retry_spin.setValue(self.config.get_retries())
        self.delay_spin.setValue(self.config.get_retry_delay())
        self.download_dir_input.setText(self.config.get_download_dir())
        
        self.font_slider.setValue(self.config.get_font_size())
    
    def clear_history(self):
        """清空历史"""
        reply = QMessageBox.question(
            self,
            '确认',
            '确定要清空所有历史记录吗？'
        )
        
        if reply == QMessageBox.Yes:
            self.history.clear_all_records()
            self.show_info_bar('历史记录已清空', '成功', InfoBarPosition.TOP)
    
    def show_info_bar(self, text: str, title: str, pos):
        """显示信息栏"""
        InfoBar.success(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=pos,
            duration=3000,
            parent=self
        )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = MangaDownloaderWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

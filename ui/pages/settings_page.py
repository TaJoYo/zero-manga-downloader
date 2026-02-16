#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设置页视图
"""

from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox, QHBoxLayout, QLabel, QMessageBox, QSlider, QSpinBox, QVBoxLayout, QWidget, QCheckBox
from qfluentwidgets import LineEdit, PushButton, ScrollArea, SimpleCardWidget

from ui.style.fluent_style import SCROLL_AREA_STYLE


class SettingsPageView(QWidget):
    """设置页视图（仅负责 UI 组件与布局）"""

    def __init__(
        self,
        on_select_download_dir: Callable,
        on_clear_history: Callable,
        on_save_settings: Callable,
        on_font_preview_change: Callable,
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName('SettingsPage')
        self._build_ui(
            on_select_download_dir,
            on_clear_history,
            on_save_settings,
            on_font_preview_change
        )

    def _build_ui(
        self,
        on_select_download_dir: Callable,
        on_clear_history: Callable,
        on_save_settings: Callable,
        on_font_preview_change: Callable
    ):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = ScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(SCROLL_AREA_STYLE)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(30, 30, 30, 30)
        scroll_layout.setSpacing(20)

        self._build_download_card(scroll_layout, on_select_download_dir)
        self._build_ui_card(scroll_layout, on_font_preview_change)
        self._build_history_card(scroll_layout, on_clear_history)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(30, 15, 30, 15)
        self.save_btn = PushButton('💾 保存设置')
        self.save_btn.setMinimumHeight(45)
        self.save_btn.clicked.connect(on_save_settings)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn, 0)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

    def _build_download_card(self, parent_layout: QVBoxLayout, on_select_download_dir: Callable):
        download_card = SimpleCardWidget()
        dl_layout = QVBoxLayout(download_card)
        dl_layout.setContentsMargins(20, 20, 20, 20)
        dl_layout.setSpacing(18)

        dl_title = QLabel('下载设置')
        dl_title.setObjectName('dl_title')
        dl_layout.addWidget(dl_title)

        thread_row = self._create_setting_row('线程数:', 120)
        self.threads_slider = QSlider(Qt.Horizontal)
        self.threads_slider.setMinimum(1)
        self.threads_slider.setMaximum(50)
        self.threads_slider.setValue(15)
        self.threads_slider.setMinimumHeight(32)
        self.threads_value_label = QLabel('15')
        self.threads_value_label.setMinimumWidth(30)
        self.threads_slider.valueChanged.connect(lambda v: self.threads_value_label.setText(str(v)))
        thread_row.addWidget(self.threads_slider, 1)
        thread_row.addWidget(self.threads_value_label, 0)
        dl_layout.addLayout(thread_row)

        self.note = QLabel('⚠ 过多线程可能被封IP，建议5-20')
        self.note.setStyleSheet('color: #FF9800; font-size: 12px; margin-left: 130px;')
        dl_layout.addWidget(self.note)

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

        timeout_row = self._create_setting_row('请求超时:', 120)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(3)
        self.timeout_spin.setMaximum(120)
        self.timeout_spin.setValue(15)
        self.timeout_spin.setMaximumWidth(100)
        self.timeout_spin.setMinimumHeight(32)
        timeout_row.addWidget(self.timeout_spin, 0)
        timeout_row.addWidget(QLabel('秒'), 0)
        timeout_row.addStretch()
        dl_layout.addLayout(timeout_row)

        format_row = self._create_setting_row('输出格式:', 120)
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItem('章节文件夹（默认）', 'folder')
        self.output_format_combo.addItem('ZIP 压缩包', 'zip')
        self.output_format_combo.addItem('CBZ 漫画包', 'cbz')
        self.output_format_combo.setMinimumHeight(32)
        self.output_format_combo.setMaximumWidth(220)
        format_row.addWidget(self.output_format_combo, 0)
        format_row.addStretch()
        dl_layout.addLayout(format_row)

        dir_row = self._create_setting_row('下载目录:', 120)
        self.download_dir_input = LineEdit()
        self.download_dir_input.setMinimumHeight(32)
        dir_row.addWidget(self.download_dir_input, 1)
        browse_btn = PushButton('浏览')
        browse_btn.setMaximumWidth(80)
        browse_btn.setMinimumHeight(32)
        browse_btn.clicked.connect(on_select_download_dir)
        dir_row.addWidget(browse_btn, 0)
        dl_layout.addLayout(dir_row)

        verify_row = self._create_setting_row('图片校验:', 120)
        self.verify_images_checkbox = QCheckBox('严格校验已存在图片（损坏自动重下）')
        verify_row.addWidget(self.verify_images_checkbox, 1)
        verify_row.addStretch()
        dl_layout.addLayout(verify_row)

        parent_layout.addWidget(download_card)

    def _build_ui_card(self, parent_layout: QVBoxLayout, on_font_preview_change: Callable):
        ui_card = SimpleCardWidget()
        ui_layout = QVBoxLayout(ui_card)
        ui_layout.setContentsMargins(20, 20, 20, 20)
        ui_layout.setSpacing(18)

        ui_title = QLabel('界面设置')
        ui_title.setObjectName('ui_title')
        ui_layout.addWidget(ui_title)

        font_row = self._create_setting_row('字体大小:', 120)
        self.font_slider = QSlider(Qt.Horizontal)
        self.font_slider.setMinimum(8)
        self.font_slider.setMaximum(16)
        self.font_slider.setMaximumWidth(250)
        self.font_slider.setMinimumHeight(32)
        self.font_slider.valueChanged.connect(on_font_preview_change)
        font_row.addWidget(self.font_slider, 0)
        font_row.addStretch()
        ui_layout.addLayout(font_row)

        parent_layout.addWidget(ui_card)

    def _build_history_card(self, parent_layout: QVBoxLayout, on_clear_history: Callable):
        history_card = SimpleCardWidget()
        hist_layout = QVBoxLayout(history_card)
        hist_layout.setContentsMargins(20, 20, 20, 20)
        hist_layout.setSpacing(18)

        hist_title = QLabel('历史记录')
        hist_title.setObjectName('hist_title')
        hist_layout.addWidget(hist_title)

        clear_btn = PushButton('🗑 清空历史')
        clear_btn.setMinimumHeight(40)
        clear_btn.clicked.connect(on_clear_history)
        hist_layout.addWidget(clear_btn)

        parent_layout.addWidget(history_card)

    def _create_setting_row(self, label_text: str, label_width: int) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(15)
        label = QLabel(label_text)
        label.setMinimumWidth(label_width)
        label.setMaximumWidth(label_width)
        label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        row.addWidget(label, 0)
        return row

    def confirm_clear_history(self) -> bool:
        reply = QMessageBox.question(self, '确认', '确定要清空所有历史记录吗？')
        return reply == QMessageBox.Yes

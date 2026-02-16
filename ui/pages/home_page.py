#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
首页视图
"""

from typing import Callable

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget
from qfluentwidgets import LineEdit, ProgressBar, PushButton, ScrollArea, SimpleCardWidget, TextEdit

from ui.style.fluent_style import SCROLL_AREA_STYLE


class HomePageView(QWidget):
    """首页视图（仅负责 UI 组件与布局）"""

    def __init__(
        self,
        on_show_history: Callable,
        on_parse_url: Callable,
        on_select_all: Callable,
        on_deselect_all: Callable,
        on_start_download: Callable,
        on_cancel_download: Callable,
        parent=None
    ):
        super().__init__(parent)
        self.setObjectName('HomePage')
        self._build_ui(
            on_show_history,
            on_parse_url,
            on_select_all,
            on_deselect_all,
            on_start_download,
            on_cancel_download
        )

    def _build_ui(
        self,
        on_show_history: Callable,
        on_parse_url: Callable,
        on_select_all: Callable,
        on_deselect_all: Callable,
        on_start_download: Callable,
        on_cancel_download: Callable
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

        self._build_url_card(scroll_layout, on_show_history, on_parse_url)
        self._build_info_card(scroll_layout)
        self._build_chapter_card(scroll_layout, on_select_all, on_deselect_all)
        self._build_control_card(scroll_layout, on_start_download, on_cancel_download)
        self._build_progress_card(scroll_layout)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        main_layout.addWidget(scroll_area)

    def _build_url_card(self, parent_layout: QVBoxLayout, on_show_history: Callable, on_parse_url: Callable):
        url_card = SimpleCardWidget()
        url_layout = QVBoxLayout(url_card)
        url_layout.setContentsMargins(20, 20, 20, 20)
        url_layout.setSpacing(12)

        url_title = QLabel('漫画URL')
        url_title.setStyleSheet('font-weight: bold;')
        url_layout.addWidget(url_title)

        self.example = QLabel('例如: https://www.zerobywai.com/pc/manga_pc.php?kuid=7887')
        self.example.setStyleSheet('color: #999;')
        self.example.setWordWrap(True)
        url_layout.addWidget(self.example)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.url_history_btn = PushButton('📋 历史')
        self.url_history_btn.setMinimumHeight(40)
        self.url_history_btn.clicked.connect(on_show_history)
        input_row.addWidget(self.url_history_btn)

        self.url_input = LineEdit()
        self.url_input.setPlaceholderText('输入漫画URL...')
        self.url_input.setMinimumHeight(40)
        input_row.addWidget(self.url_input)

        self.parse_btn = PushButton('解析')
        self.parse_btn.setMinimumHeight(40)
        self.parse_btn.clicked.connect(on_parse_url)
        input_row.addWidget(self.parse_btn)

        url_layout.addLayout(input_row)
        parent_layout.addWidget(url_card)

    def _build_info_card(self, parent_layout: QVBoxLayout):
        info_card = SimpleCardWidget()
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)
        info_layout.setSpacing(16)

        title_row = QHBoxLayout()
        title_row.setSpacing(20)
        title_label = QLabel('标题:')
        title_label.setMinimumWidth(100)
        title_label.setMaximumWidth(100)
        self.manga_title_label = QLabel('未解析')
        title_row.addWidget(title_label, 0)
        title_row.addWidget(self.manga_title_label, 1)
        info_layout.addLayout(title_row)

        chapters_row = QHBoxLayout()
        chapters_row.setSpacing(20)
        chapters_label = QLabel('章节数:')
        chapters_label.setMinimumWidth(100)
        chapters_label.setMaximumWidth(100)
        self.manga_chapters_label = QLabel('0')
        chapters_row.addWidget(chapters_label, 0)
        chapters_row.addWidget(self.manga_chapters_label, 1)
        info_layout.addLayout(chapters_row)

        parent_layout.addWidget(info_card)

    def _build_chapter_card(self, parent_layout: QVBoxLayout, on_select_all: Callable, on_deselect_all: Callable):
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
        self.select_all_btn.clicked.connect(on_select_all)
        btn_row.addWidget(self.select_all_btn)

        self.deselect_all_btn = PushButton('✗ 全不选')
        self.deselect_all_btn.setMinimumHeight(40)
        self.deselect_all_btn.clicked.connect(on_deselect_all)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        chapter_layout.addLayout(btn_row)

        self.chapter_list = QListWidget()
        self.chapter_list.setMinimumHeight(200)
        self.chapter_list.setUniformItemSizes(True)
        chapter_layout.addWidget(self.chapter_list)

        parent_layout.addWidget(chapter_card)

    def _build_control_card(self, parent_layout: QVBoxLayout, on_start_download: Callable, on_cancel_download: Callable):
        control_card = SimpleCardWidget()
        control_layout = QHBoxLayout(control_card)
        control_layout.setContentsMargins(20, 20, 20, 20)
        control_layout.setSpacing(10)

        self.download_btn = PushButton('▶ 开始下载')
        self.download_btn.setEnabled(False)
        self.download_btn.setMinimumHeight(40)
        self.download_btn.clicked.connect(on_start_download)
        control_layout.addWidget(self.download_btn)

        self.cancel_btn = PushButton('⏹ 取消')
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(on_cancel_download)
        control_layout.addWidget(self.cancel_btn)

        parent_layout.addWidget(control_card)

    def _build_progress_card(self, parent_layout: QVBoxLayout):
        progress_card = SimpleCardWidget()
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(20, 20, 20, 20)
        progress_layout.setSpacing(12)

        progress_title = QLabel('下载进度')
        progress_title.setStyleSheet('font-weight: bold;')
        progress_layout.addWidget(progress_title)

        self.phase_label = QLabel('阶段: 空闲')
        self.phase_label.setStyleSheet('color: #666;')
        progress_layout.addWidget(self.phase_label)

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

        parent_layout.addWidget(progress_card)

    def append_log(self, message: str):
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    def clear_chapters(self):
        self.chapter_list.clear()

    def populate_chapters(self, chapter_titles):
        self.chapter_list.setUpdatesEnabled(False)
        try:
            self.chapter_list.clear()
            for title in chapter_titles:
                item = QListWidgetItem(title)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                self.chapter_list.addItem(item)
            if self.chapter_list.count() > 0:
                self.chapter_list.scrollToTop()
        finally:
            self.chapter_list.setUpdatesEnabled(True)

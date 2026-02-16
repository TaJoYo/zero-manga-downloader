#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口与应用入口装配
"""

import sys
from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import QThread, Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QListWidget, QListWidgetItem, QVBoxLayout
from qfluentwidgets import (
    FluentIcon,
    FluentWindow,
    InfoBar,
    InfoBarPosition,
    Theme,
    setTheme,
    setThemeColor,
)

from config_manager import ConfigManager
from downloader import MangaDownloader
from history_manager import HistoryManager
from manga_parser import MangaParser
from ui.pages.home_page import HomePageView
from ui.pages.settings_page import SettingsPageView
from ui.presenter.download_presenter import DownloadPresenter
from ui.state.download_state import ControlState
from ui.style.fluent_style import build_global_stylesheet


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
        def progress_callback(status, url, _path, detail=''):
            self.progress_signal.emit(status, url, detail)

        def chapter_callback(status, current, total, name, stats=None):
            self.chapter_signal.emit(status, current, total, name, stats or {})

        stats = self.downloader.download_manga(
            self.manga_info,
            self.chapters,
            self.save_dir,
            progress_callback,
            chapter_callback,
        )
        self.finished_signal.emit(stats)


class MangaDownloaderWindow(FluentWindow):
    """主窗口 - Fluent 风格"""

    def __init__(self):
        super().__init__()

        self.config = ConfigManager()
        self.history = HistoryManager(max_records=self.config.get_max_history_records())
        self.parser = MangaParser()

        self.downloader = None
        self.download_thread = None
        self.current_manga: Dict = {}
        self.control_state = ControlState.IDLE

        self.apply_theme()
        self.init_ui()
        self.presenter = DownloadPresenter(
            view=self.home_page,
            apply_control_state=self.apply_control_state,
            show_info_bar=self.show_info_bar,
            add_history_record=self._add_history_record,
            is_history_enabled=self.config.is_history_enabled,
        )
        self.load_config()
        self.apply_font()
        self.presenter.set_idle_view()
        self.apply_control_state(ControlState.IDLE)

    def apply_theme(self):
        """固定为亮色主题"""
        setTheme(Theme.LIGHT)
        setThemeColor('#2196F3')

    def apply_font(self):
        """应用全局字体和尺寸样式"""
        font_size = self.config.get_font_size()
        font = QFont("Microsoft YaHei, Segoe UI, 宋体")
        font.setPointSize(font_size)
        font.setStyleStrategy(QFont.PreferAntialias)
        QApplication.instance().setFont(font)

        stylesheet, metrics = build_global_stylesheet(font_size)
        QApplication.instance().setStyleSheet(stylesheet)

        self.home_page.example.setStyleSheet('color: #999;')
        self.home_page.status_label.setStyleSheet('color: #666;')
        self.settings_page.note.setStyleSheet('color: #FF9800; font-size: 12px; margin-left: 130px;')

        self.home_page.url_history_btn.setMinimumWidth(metrics['large_btn_width'])
        self.home_page.parse_btn.setMinimumWidth(metrics['btn_width_2char'])
        self.home_page.select_all_btn.setMinimumWidth(metrics['btn_width_2char'])
        self.home_page.deselect_all_btn.setMinimumWidth(metrics['btn_width_3char'])
        self.settings_page.output_format_combo.setMinimumHeight(metrics['input_height'])
        self.settings_page.timeout_spin.setMinimumHeight(metrics['input_height'])

    def init_ui(self):
        self.setWindowTitle('零漫画下载器')
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 600)
        self.navigationInterface.setReturnButtonVisible(False)

        self.home_page = HomePageView(
            on_show_history=self.show_url_history,
            on_parse_url=self.parse_url,
            on_select_all=lambda: self.set_chapter_selection(True),
            on_deselect_all=lambda: self.set_chapter_selection(False),
            on_start_download=self.start_download,
            on_cancel_download=self.cancel_download,
        )
        self.settings_page = SettingsPageView(
            on_select_download_dir=self.select_download_dir,
            on_clear_history=self.clear_history,
            on_save_settings=self.save_settings,
            on_font_preview_change=self.on_font_preview_change,
        )

        self.addSubInterface(self.home_page, FluentIcon.HOME, '首页')
        self.addSubInterface(self.settings_page, FluentIcon.SETTING, '设置')
        self.home_page.chapter_list.itemChanged.connect(lambda *_: self._update_download_button_state())

    def apply_control_state(self, state: ControlState):
        """下载控制区状态机"""
        self.control_state = state

        if state == ControlState.IDLE:
            self.home_page.parse_btn.setEnabled(True)
            self.home_page.cancel_btn.setEnabled(False)
            self.home_page.cancel_btn.setText('⏹ 取消')
            self._update_download_button_state()
            return

        if state == ControlState.RUNNING:
            self.home_page.download_btn.setEnabled(False)
            self.home_page.parse_btn.setEnabled(False)
            self.home_page.cancel_btn.setEnabled(True)
            self.home_page.cancel_btn.setText('⏹ 取消')
            return

        if state == ControlState.CANCELLING:
            self.home_page.download_btn.setEnabled(False)
            self.home_page.parse_btn.setEnabled(False)
            self.home_page.cancel_btn.setEnabled(False)
            self.home_page.cancel_btn.setText('⏳ 取消中')

    def on_font_preview_change(self, value: int):
        self.config.set_font_size(value)
        self.apply_font()

    def parse_url(self):
        url = self.home_page.url_input.text().strip()
        if not url:
            self.show_info_bar('请输入漫画URL', '错误', InfoBarPosition.TOP, 'error')
            return

        self.presenter.set_phase('parsing')
        self.home_page.status_label.setText('解析中...')
        self.home_page.parse_btn.setEnabled(False)
        self.home_page.append_log('⏳ 正在解析URL...')

        try:
            manga_info = self.parser.parse_manga_url(url)
            self.current_manga = manga_info

            self.home_page.manga_title_label.setText(manga_info['title'])
            self.home_page.manga_chapters_label.setText(str(manga_info['total_chapters']))
            self.home_page.populate_chapters([chapter['title'] for chapter in manga_info['chapters']])

            self.presenter.set_phase('idle')
            self.home_page.status_label.setText('解析完成，可开始下载')
            self.home_page.append_log(f'✓ 解析成功！找到 {manga_info["total_chapters"]} 个章节')
            if manga_info.get('manga_id'):
                self.home_page.append_log(f'  漫画ID: {manga_info["manga_id"]}')

            if self.config.is_history_enabled():
                self._add_history_record(url, manga_info['title'], manga_info['total_chapters'], 'parsed')
        except Exception as exc:
            self.presenter.set_phase('failed')
            self.home_page.append_log(f'[错误] 解析失败: {exc}')
            self.show_info_bar(f'解析URL失败: {exc}', '错误', InfoBarPosition.TOP, 'error')
            self.home_page.status_label.setText('解析失败')
        finally:
            if self.control_state == ControlState.IDLE:
                self.home_page.parse_btn.setEnabled(True)
            self._update_download_button_state()

    def set_chapter_selection(self, checked: bool):
        state = Qt.Checked if checked else Qt.Unchecked
        chapter_list = self.home_page.chapter_list
        chapter_list.blockSignals(True)
        try:
            for i in range(chapter_list.count()):
                chapter_list.item(i).setCheckState(state)
        finally:
            chapter_list.blockSignals(False)
        self._update_download_button_state()

    def _selected_chapter_indices(self) -> List[int]:
        selected = []
        for i in range(self.home_page.chapter_list.count()):
            if self.home_page.chapter_list.item(i).checkState() == Qt.Checked:
                selected.append(i)
        return selected

    def _update_download_button_state(self):
        can_download = (
            self.control_state == ControlState.IDLE
            and bool(self.current_manga)
            and bool(self._selected_chapter_indices())
        )
        self.home_page.download_btn.setEnabled(can_download)

    def start_download(self):
        if not self.current_manga:
            self.show_info_bar('请先解析漫画链接', '提示', InfoBarPosition.TOP, 'warning')
            return

        selected_chapters = self._selected_chapter_indices()
        if not selected_chapters:
            self.show_info_bar('请至少选择一个章节', '提示', InfoBarPosition.TOP, 'warning')
            return

        download_dir = Path(self.config.get_download_dir())
        download_dir.mkdir(parents=True, exist_ok=True)

        self.downloader = MangaDownloader(
            threads=self.config.get_download_threads(),
            retries=self.config.get_retries(),
            retry_delay=self.config.get_retry_delay(),
            timeout=self.config.get_timeout(),
            verify_images=self.config.get_verify_images(),
            output_format=self.config.get_output_format(),
        )
        self.download_thread = DownloadThread(
            self.downloader,
            self.current_manga,
            selected_chapters,
            str(download_dir),
        )
        self.download_thread.progress_signal.connect(self.presenter.on_download_progress)
        self.download_thread.chapter_signal.connect(self.presenter.on_chapter_progress)
        self.download_thread.finished_signal.connect(self.on_download_finished)

        output_format_text = self.settings_page.output_format_combo.currentText()
        self.presenter.begin_download(self.current_manga, len(selected_chapters), output_format_text)
        self.download_thread.start()

    def cancel_download(self):
        if not self.downloader:
            return
        self.downloader.cancel()
        self.presenter.mark_cancelling()

    def on_download_finished(self, stats: Dict):
        self.presenter.on_download_finished(stats)
        self._update_download_button_state()

    def show_url_history(self):
        records = self.history.get_recent_records(10)
        if not records:
            self.show_info_bar('暂无历史记录', '提示', InfoBarPosition.TOP, 'info')
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('历史记录')
        dialog.setGeometry(200, 200, 600, 400)
        layout = QVBoxLayout()
        list_widget = QListWidget()

        for record in records:
            item = QListWidgetItem(f"{record['title']} ({record['chapters_count']}章)")
            item.setData(Qt.UserRole, record['url'])
            list_widget.addItem(item)

        list_widget.itemDoubleClicked.connect(lambda item: self.load_history_item(item.data(Qt.UserRole), dialog))
        layout.addWidget(list_widget)
        dialog.setLayout(layout)
        dialog.exec_()

    def load_history_item(self, url: str, dialog: QDialog):
        self.home_page.url_input.setText(url)
        dialog.close()

    def select_download_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            '选择下载目录',
            self.settings_page.download_dir_input.text(),
        )
        if directory:
            self.settings_page.download_dir_input.setText(directory)

    def save_settings(self):
        save_results = [
            self.config.set_download_threads(self.settings_page.threads_slider.value()),
            self.config.set_retries(self.settings_page.retry_spin.value()),
            self.config.set_retry_delay(self.settings_page.delay_spin.value()),
            self.config.set_timeout(self.settings_page.timeout_spin.value()),
            self.config.set_output_format(self.settings_page.output_format_combo.currentData()),
            self.config.set_download_dir(self.settings_page.download_dir_input.text().strip()),
            self.config.set_verify_images(self.settings_page.verify_images_checkbox.isChecked()),
            self.config.set_font_size(self.settings_page.font_slider.value()),
        ]
        self.apply_font()

        if all(save_results):
            self.show_info_bar('设置已保存', '成功', InfoBarPosition.TOP, 'success')
        else:
            self.show_info_bar('部分设置保存失败，请检查文件权限', '警告', InfoBarPosition.TOP, 'warning')

    def load_config(self):
        try:
            self.settings_page.threads_slider.setValue(self.config.get_download_threads())
            self.settings_page.retry_spin.setValue(self.config.get_retries())
            self.settings_page.delay_spin.setValue(self.config.get_retry_delay())
            self.settings_page.timeout_spin.setValue(self.config.get_timeout())
            self.settings_page.download_dir_input.setText(self.config.get_download_dir())
            self.settings_page.verify_images_checkbox.setChecked(self.config.get_verify_images())
            self.settings_page.font_slider.setValue(self.config.get_font_size())

            output_format = self.config.get_output_format()
            output_idx = self.settings_page.output_format_combo.findData(output_format)
            self.settings_page.output_format_combo.setCurrentIndex(max(0, output_idx))
        except Exception as exc:
            self.show_info_bar(f'加载配置失败: {exc}', '警告', InfoBarPosition.TOP, 'warning')

    def clear_history(self):
        if not self.settings_page.confirm_clear_history():
            return
        self.history.clear_all_records()
        self.show_info_bar('历史记录已清空', '成功', InfoBarPosition.TOP, 'success')

    def _add_history_record(self, url: str, title: str, chapters_count: int, status: str):
        self.history.add_record(url, title, chapters_count, status)

    def show_info_bar(self, text: str, title: str, pos, level: str = 'success'):
        builders = {
            'success': InfoBar.success,
            'error': InfoBar.error,
            'warning': InfoBar.warning,
            'info': InfoBar.info,
        }
        builder = builders.get(level, InfoBar.success)
        builder(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=pos,
            duration=3000,
            parent=self,
        )


def main():
    app = QApplication(sys.argv)
    window = MangaDownloaderWindow()
    window.show()
    sys.exit(app.exec_())

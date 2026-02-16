#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载流程 Presenter
"""

from pathlib import Path
from typing import Callable, Dict, Optional

from qfluentwidgets import InfoBarPosition

from ui.pages.home_page import HomePageView
from ui.state.download_state import ControlState, DownloadUIState


class DownloadPresenter:
    """负责将下载线程信号映射为 UI 状态"""

    PHASE_LABELS = {
        'idle': '空闲',
        'parsing': '解析中',
        'probing': '探测中',
        'downloading': '下载中',
        'packaging': '打包中',
        'completed': '完成',
        'failed': '失败',
        'cancelling': '取消中',
        'cancelled': '已取消',
    }

    def __init__(
        self,
        view: HomePageView,
        apply_control_state: Callable[[ControlState], None],
        show_info_bar: Callable[[str, str, object, str], None],
        add_history_record: Callable[[str, str, int, str], None],
        is_history_enabled: Callable[[], bool],
    ):
        self.view = view
        self.state = DownloadUIState()
        self._apply_control_state = apply_control_state
        self._show_info_bar = show_info_bar
        self._add_history_record = add_history_record
        self._is_history_enabled = is_history_enabled

        self.current_manga: Optional[Dict] = None
        self.selected_chapter_count = 0

    def set_phase(self, phase: str):
        self.state.phase = phase
        display = self.PHASE_LABELS.get(phase, phase)
        self.view.phase_label.setText(f'阶段: {display}')

    def set_idle_view(self):
        self.state = DownloadUIState()
        self.set_phase('idle')
        self.view.progress_bar.setValue(0)
        self.view.status_label.setText('就绪')

    def begin_download(self, current_manga: Dict, selected_chapter_count: int, output_format_text: str):
        self.current_manga = current_manga
        self.selected_chapter_count = selected_chapter_count

        self.state.reset_for_new_download()
        self.set_phase('downloading')
        self._apply_control_state(ControlState.RUNNING)

        self.view.progress_bar.setValue(0)
        self.view.status_label.setText('下载准备中...')
        self.view.append_log(f'\n▶ 开始下载 {selected_chapter_count} 个章节...')
        self.view.append_log(f'  输出格式: {output_format_text}')

    def mark_cancelling(self):
        if self.state.control_state in {ControlState.IDLE, ControlState.CANCELLING}:
            return
        self.state.control_state = ControlState.CANCELLING
        self.set_phase('cancelling')
        self._apply_control_state(ControlState.CANCELLING)
        self.view.status_label.setText('取消中...')
        self.view.append_log('⏹ 正在取消下载...')

    def on_download_progress(self, status: str, url: str, detail: str):
        file_hint = Path(url).name if url else ''

        if status == 'success':
            self.state.record_image_result('success')
            self._refresh_image_progress()
            return

        if status == 'skipped':
            self.state.record_image_result('skipped')
            self._refresh_image_progress()
            return

        if status == 'retry':
            self.view.append_log(f'[重试] {file_hint} - {detail}')
            return

        if status in {'http_error', 'error', 'not_found'}:
            self.state.record_image_result(status)
            self._refresh_image_progress()
            if status == 'not_found':
                self.view.append_log(f'[错误] 图片不存在: {file_hint}')
            elif status == 'http_error':
                self.view.append_log(f'[错误] HTTP错误: {file_hint} - {detail}')
            else:
                self.view.append_log(f'[错误] 下载异常: {file_hint} - {detail}')
            return

        if status == 'cancelled':
            self.view.append_log('[取消] 当前图片下载已取消')

    def on_chapter_progress(self, status: str, current: int, total: int, name: str, stats: Dict):
        phase = stats.get('phase')
        if phase:
            self.set_phase(str(phase))

        if status == 'start':
            self.set_phase('downloading')
            self.view.status_label.setText(f'正在下载: {name} ({current}/{total})')
            self.view.append_log(f'[{current}/{total}] ⬇ {name}')
            return

        if status == 'images_total':
            chapter_images = int(stats.get('chapter_images', 0))
            planned_images = int(stats.get('planned_images', self.state.planned_images))
            self.state.planned_images = max(self.state.planned_images, planned_images)
            self.view.append_log(
                f'[{current}/{total}] [信息] 本章图片: {chapter_images}，累计计划: {self.state.planned_images}'
            )
            self._refresh_image_progress()
            return

        if status == 'complete':
            success = int(stats.get('success', 0))
            failed = int(stats.get('failed', 0))
            skipped = int(stats.get('skipped', 0))
            self.set_phase('downloading')
            self.view.append_log(f'[{current}/{total}] ✓ {name} - {success}成/{failed}失/{skipped}跳')
            return

        if status == 'failed':
            self.set_phase('failed')
            error_msg = stats.get('error', '未知错误')
            self.view.append_log(f'[{current}/{total}] [错误] {name} - {error_msg}')
            return

        if status == 'info':
            message = str(stats.get('message', '')).strip()
            if not message:
                return
            if '探测' in message:
                self.set_phase('probing')
            elif '打包' in message:
                self.set_phase('packaging')
            self.view.append_log(f'[{current}/{total}] [信息] {message}')
            return

        if status == 'cancelled':
            self.set_phase('cancelled')
            self.view.status_label.setText(f'已取消: {name} ({current}/{total})')
            self.view.append_log(f'[{current}/{total}] [取消] 已取消 {name}')

    def on_download_finished(self, stats: Dict):
        self.state.sync_from_stats(stats)
        self.state.control_state = ControlState.IDLE
        self._apply_control_state(ControlState.IDLE)

        total_chapters = int(stats.get('total_chapters', self.selected_chapter_count))
        success_chapters = int(stats.get('success_chapters', 0))
        success_images = int(stats.get('success_images', 0))
        failed_images = int(stats.get('failed_images', 0))
        skipped_images = int(stats.get('skipped_images', 0))
        elapsed_ms = int(stats.get('elapsed_ms', 0))
        elapsed_text = f'{elapsed_ms / 1000:.1f}s' if elapsed_ms > 0 else '未知'

        if stats.get('cancelled'):
            cancelled_chapter = stats.get('cancelled_chapter') or '未知章节'
            self.set_phase('cancelled')
            self._refresh_image_progress()
            self.view.status_label.setText('⏹ 已取消')
            self.view.append_log('\n⏹ 下载已取消')
            self.view.append_log(f'  取消位置: {cancelled_chapter}')
            self.view.append_log(f'  章节: {success_chapters}/{total_chapters}')
            self.view.append_log(f'  图片: {success_images}成/{failed_images}失/{skipped_images}跳')
            self.view.append_log(f'  耗时: {elapsed_text}')

            self._write_history(total_chapters, 'cancelled')
            self._show_info_bar(
                f'已取消于: {cancelled_chapter}  |  图片: {success_images}成/{failed_images}失',
                '已取消',
                InfoBarPosition.TOP,
                'warning',
            )
            return

        if self.state.planned_images > 0:
            self.view.progress_bar.setValue(100)
        self.set_phase('completed')
        self.view.status_label.setText('✓ 下载完成')
        self.view.append_log('\n✓✓✓ 下载完成！')
        self.view.append_log(f'  章节: {success_chapters}/{total_chapters}')
        self.view.append_log(f'  图片: {success_images}成/{failed_images}失/{skipped_images}跳')
        self.view.append_log(f'  耗时: {elapsed_text}')

        history_status = 'completed' if success_chapters == total_chapters else 'partial'
        self._write_history(total_chapters, history_status)
        self._show_info_bar(
            f'成功: {success_chapters}/{total_chapters}  |  图片: {success_images}成/{failed_images}失',
            '完成',
            InfoBarPosition.TOP,
            'success',
        )

    def _write_history(self, total_chapters: int, status: str):
        if not self.current_manga or not self._is_history_enabled():
            return
        self._add_history_record(
            self.current_manga['url'],
            self.current_manga['title'],
            total_chapters,
            status,
        )

    def _refresh_image_progress(self):
        self.view.progress_bar.setValue(self.state.progress_percent)
        if self.state.control_state in {ControlState.RUNNING, ControlState.CANCELLING}:
            prefix = '取消中' if self.state.control_state == ControlState.CANCELLING else '下载中'
            self.view.status_label.setText(
                f'{prefix}: 图片 {self.state.processed_images}/{self.state.planned_images} '
                f'({self.state.success_images}成/{self.state.failed_images}失/{self.state.skipped_images}跳)'
            )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载 UI 状态模型
"""

from dataclasses import dataclass
from enum import Enum


class ControlState(Enum):
    """下载控制区状态"""
    IDLE = 'idle'
    RUNNING = 'running'
    CANCELLING = 'cancelling'


@dataclass
class DownloadUIState:
    """下载过程 UI 状态"""
    phase: str = 'idle'
    planned_images: int = 0
    processed_images: int = 0
    success_images: int = 0
    failed_images: int = 0
    skipped_images: int = 0
    control_state: ControlState = ControlState.IDLE

    def reset_for_new_download(self):
        self.phase = 'downloading'
        self.planned_images = 0
        self.processed_images = 0
        self.success_images = 0
        self.failed_images = 0
        self.skipped_images = 0
        self.control_state = ControlState.RUNNING

    @property
    def progress_percent(self) -> int:
        if self.planned_images <= 0:
            return 0
        progress = int((self.processed_images / self.planned_images) * 100)
        return max(0, min(progress, 100))

    def record_image_result(self, status: str):
        """记录图片级结果"""
        if status == 'success':
            self.success_images += 1
            self.processed_images += 1
        elif status == 'skipped':
            self.skipped_images += 1
            self.processed_images += 1
        elif status in {'http_error', 'error', 'not_found'}:
            self.failed_images += 1
            self.processed_images += 1

    def sync_from_stats(self, stats: dict):
        """从下载结果统计同步状态"""
        self.success_images = int(stats.get('success_images', 0))
        self.failed_images = int(stats.get('failed_images', 0))
        self.skipped_images = int(stats.get('skipped_images', 0))
        self.processed_images = self.success_images + self.failed_images + self.skipped_images
        self.planned_images = max(
            self.planned_images,
            int(stats.get('planned_images', 0)),
            int(stats.get('total_images', 0))
        )

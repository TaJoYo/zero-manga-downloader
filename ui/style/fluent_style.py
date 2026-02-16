#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fluent UI 样式与尺寸计算
"""

from typing import Dict, Tuple


SCROLL_AREA_STYLE = """
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
"""


def build_global_stylesheet(font_size: int) -> Tuple[str, Dict[str, int]]:
    """
    构建全局样式表与尺寸指标
    """
    btn_height = max(36, font_size + 16)
    btn_width_2char = max(80, font_size * 8)
    btn_width_3char = max(120, font_size * 15)
    input_height = max(36, font_size + 16)
    large_btn_width = max(100, font_size * 10)
    title_size = max(13, font_size + 3)
    slider_handle = "#2196F3"
    slider_handle_hover = "#1976D2"

    stylesheet = f"""
        QLineEdit {{ padding: 4px; min-height: {input_height}px; }}
        QSpinBox {{ padding: 2px; min-height: {input_height}px; }}
        QComboBox {{ padding: 2px; min-height: {input_height}px; }}
        QPushButton {{ padding: 6px 12px; min-height: {btn_height}px; }}

        #dl_title, #ui_title, #hist_title {{
            font-weight: bold;
            font-size: {title_size}pt;
        }}

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

    metrics = {
        'btn_height': btn_height,
        'btn_width_2char': btn_width_2char,
        'btn_width_3char': btn_width_3char,
        'input_height': input_height,
        'large_btn_width': large_btn_width,
    }
    return stylesheet, metrics

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器 - 管理用户配置和设置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        # 账户设置
        'account': {
            'username': '',
            'password': '',
            'cookies': {}
        },
        
        # 下载设置
        'download': {
            'threads': 15,  # 下载线程数
            'retries': 3,   # 重试次数
            'retry_delay': 2,  # 重试延迟(秒)
            'download_dir': str(Path.home() / 'Downloads'),  # 下载目录
            'timeout': 15,  # 请求超时(秒)
            'verify_images': True,  # 严格校验图片完整性
        },
        
        # 界面设置
        'ui': {
            'theme': 'light',  # light, dark, auto
            'language': 'zh-CN',
            'window_size': [900, 700],
            'window_position': None,
            'font_size': 10  # 基础字体大小
        },
        
        # 历史记录设置
        'history': {
            'enabled': True,
            'max_records': 100
        }
    }
    
    def __init__(self, config_file: str = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为用户目录下的.zero_manga_config.json
        """
        if config_file is None:
            config_file = Path.home() / '.zero_manga_config.json'
        
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并默认配置和加载的配置
                    return self._merge_config(self.DEFAULT_CONFIG.copy(), loaded_config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.DEFAULT_CONFIG.copy()
        else:
            # 创建默认配置文件
            self.save_config()
            return self.DEFAULT_CONFIG.copy()
    
    def _merge_config(self, default: Dict, loaded: Dict) -> Dict:
        """递归合并配置，保留默认配置中的所有键"""
        for key, value in default.items():
            if key in loaded:
                if isinstance(value, dict) and isinstance(loaded[key], dict):
                    default[key] = self._merge_config(value, loaded[key])
                else:
                    default[key] = loaded[key]
        return default
    
    def save_config(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，用.分隔，例如 'download.threads'
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        设置配置值
        
        Args:
            key_path: 配置键路径，用.分隔
            value: 要设置的值
        
        Returns:
            是否设置成功
        """
        keys = key_path.split('.')
        config = self.config
        
        # 导航到最后一个键之前
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        return self.save_config()
    
    def get_download_threads(self) -> int:
        """获取下载线程数"""
        return self.get('download.threads', 15)
    
    def set_download_threads(self, threads: int) -> bool:
        """设置下载线程数"""
        threads = max(1, min(50, threads))
        return self.set('download.threads', threads)
    
    def get_download_dir(self) -> str:
        """获取下载目录"""
        return self.get('download.download_dir', str(Path.home() / 'Downloads'))
    
    def set_download_dir(self, directory: str) -> bool:
        """设置下载目录"""
        return self.set('download.download_dir', directory)
    
    def get_retries(self) -> int:
        """获取重试次数"""
        return self.get('download.retries', 3)
    
    def set_retries(self, retries: int) -> bool:
        """设置重试次数"""
        retries = max(1, min(10, retries))
        return self.set('download.retries', retries)
    
    def get_retry_delay(self) -> int:
        """获取重试延迟"""
        return self.get('download.retry_delay', 2)
    
    def set_retry_delay(self, delay: int) -> bool:
        """设置重试延迟"""
        delay = max(0, min(60, delay))
        return self.set('download.retry_delay', delay)

    def get_verify_images(self) -> bool:
        """是否严格校验图片完整性"""
        return bool(self.get('download.verify_images', True))

    def set_verify_images(self, enabled: bool) -> bool:
        """设置图片严格校验开关"""
        return self.set('download.verify_images', bool(enabled))
    
    def get_username(self) -> str:
        """获取用户名"""
        return self.get('account.username', '')
    
    def set_username(self, username: str) -> bool:
        """设置用户名"""
        return self.set('account.username', username)
    
    def get_password(self) -> str:
        """获取密码"""
        return self.get('account.password', '')
    
    def set_password(self, password: str) -> bool:
        """设置密码"""
        return self.set('account.password', password)
    
    def get_cookies(self) -> Dict[str, str]:
        """获取Cookie"""
        return self.get('account.cookies', {})
    
    def set_cookies(self, cookies: Dict[str, str]) -> bool:
        """设置Cookie"""
        return self.set('account.cookies', cookies)
    
    def is_history_enabled(self) -> bool:
        """检查历史记录是否启用"""
        return self.get('history.enabled', True)
    
    def get_max_history_records(self) -> int:
        """获取最大历史记录数"""
        return self.get('history.max_records', 100)
    
    def get_theme(self) -> str:
        """获取主题设置"""
        return self.get('ui.theme', 'light')
    
    def set_theme(self, theme: str) -> bool:
        """设置主题"""
        if theme in ['light', 'dark', 'auto']:
            return self.set('ui.theme', theme)
        return False
    
    def get_font_size(self) -> int:
        """获取字体大小"""
        return self.get('ui.font_size', 10)
    
    def set_font_size(self, size: int) -> bool:
        """设置字体大小"""
        size = max(8, min(16, size))
        return self.set('ui.font_size', size)
    
    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save_config()
    
    def export_config(self, file_path: str) -> bool:
        """导出配置到指定文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def import_config(self, file_path: str) -> bool:
        """从文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
                self.config = self._merge_config(self.DEFAULT_CONFIG.copy(), imported)
                return self.save_config()
        except:
            return False

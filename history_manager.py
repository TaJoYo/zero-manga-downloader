#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录管理器 - 管理下载历史
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional


class HistoryManager:
    """历史记录管理器"""
    
    def __init__(self, history_file: str = None, max_records: int = 100):
        """
        初始化历史记录管理器
        
        Args:
            history_file: 历史记录文件路径
            max_records: 最大记录数
        """
        if history_file is None:
            history_file = Path.home() / '.zero_manga_history.json'
        
        self.history_file = Path(history_file)
        self.max_records = max_records
        self.history = self._load_history()
    
    def _load_history(self) -> List[Dict]:
        """加载历史记录"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载历史记录失败: {e}")
                return []
        return []
    
    def _save_history(self) -> bool:
        """保存历史记录"""
        try:
            # 确保目录存在
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"保存历史记录失败: {e}")
            return False
    
    def add_record(self, url: str, title: str, chapters_count: int, 
                   status: str = 'completed') -> bool:
        """
        添加下载记录
        
        Args:
            url: 漫画URL
            title: 漫画标题
            chapters_count: 章节数量
            status: 下载状态 (completed/failed/partial)
        
        Returns:
            是否添加成功
        """
        # 检查是否已存在
        for record in self.history:
            if record['url'] == url:
                # 更新现有记录
                record['title'] = title
                record['chapters_count'] = chapters_count
                record['status'] = status
                record['last_download'] = datetime.now().isoformat()
                record['download_count'] = record.get('download_count', 0) + 1
                return self._save_history()
        
        # 添加新记录
        record = {
            'url': url,
            'title': title,
            'chapters_count': chapters_count,
            'status': status,
            'first_download': datetime.now().isoformat(),
            'last_download': datetime.now().isoformat(),
            'download_count': 1
        }
        
        self.history.insert(0, record)
        
        # 限制记录数量
        if len(self.history) > self.max_records:
            self.history = self.history[:self.max_records]
        
        return self._save_history()
    
    def get_all_records(self) -> List[Dict]:
        """获取所有历史记录"""
        return self.history.copy()
    
    def get_recent_records(self, count: int = 10) -> List[Dict]:
        """
        获取最近的记录
        
        Args:
            count: 记录数量
        
        Returns:
            历史记录列表
        """
        return self.history[:count]
    
    def search_records(self, keyword: str) -> List[Dict]:
        """
        搜索历史记录
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的记录列表
        """
        keyword = keyword.lower()
        results = []
        
        for record in self.history:
            if (keyword in record['title'].lower() or 
                keyword in record['url'].lower()):
                results.append(record)
        
        return results
    
    def get_record_by_url(self, url: str) -> Optional[Dict]:
        """
        根据URL获取记录
        
        Args:
            url: 漫画URL
        
        Returns:
            历史记录，如果不存在返回None
        """
        for record in self.history:
            if record['url'] == url:
                return record.copy()
        return None
    
    def delete_record(self, url: str) -> bool:
        """
        删除记录
        
        Args:
            url: 要删除的漫画URL
        
        Returns:
            是否删除成功
        """
        original_length = len(self.history)
        self.history = [r for r in self.history if r['url'] != url]
        
        if len(self.history) < original_length:
            return self._save_history()
        
        return False
    
    def clear_all_records(self) -> bool:
        """清空所有历史记录"""
        self.history = []
        return self._save_history()
    
    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        total_records = len(self.history)
        total_chapters = sum(r.get('chapters_count', 0) for r in self.history)
        completed = len([r for r in self.history if r.get('status') == 'completed'])
        failed = len([r for r in self.history if r.get('status') == 'failed'])
        
        return {
            'total_records': total_records,
            'total_chapters': total_chapters,
            'completed': completed,
            'failed': failed,
            'success_rate': f"{(completed / total_records * 100):.1f}%" if total_records > 0 else "0%"
        }
    
    def update_record_status(self, url: str, status: str) -> bool:
        """
        更新记录状态
        
        Args:
            url: 漫画URL
            status: 新状态
        
        Returns:
            是否更新成功
        """
        for record in self.history:
            if record['url'] == url:
                record['status'] = status
                record['last_download'] = datetime.now().isoformat()
                return self._save_history()
        
        return False
    
    def export_history(self, file_path: str) -> bool:
        """
        导出历史记录到文件
        
        Args:
            file_path: 导出文件路径
        
        Returns:
            是否导出成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False
    
    def import_history(self, file_path: str) -> bool:
        """
        从文件导入历史记录
        
        Args:
            file_path: 导入文件路径
        
        Returns:
            是否导入成功
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = json.load(f)
                
                # 合并导入的记录
                for record in imported:
                    # 检查是否已存在
                    existing = False
                    for existing_record in self.history:
                        if existing_record['url'] == record['url']:
                            existing = True
                            break
                    
                    if not existing:
                        self.history.append(record)
                
                # 限制记录数量
                if len(self.history) > self.max_records:
                    self.history = self.history[:self.max_records]
                
                return self._save_history()
        except:
            return False

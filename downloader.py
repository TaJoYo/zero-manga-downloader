#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载器核心模块 - 处理漫画下载逻辑
"""

import os
import time
import requests
from pathlib import Path
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


class MangaDownloader:
    """漫画下载器"""
    
    def __init__(self, threads: int = 15, retries: int = 3, 
                 retry_delay: int = 2, timeout: int = 15):
        """
        初始化下载器
        
        Args:
            threads: 下载线程数
            retries: 重试次数
            retry_delay: 重试延迟(秒)
            timeout: 请求超时(秒)
        """
        self.threads = threads
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.zerobywai.com/'
        })
        
        # 下载统计
        self.stats = {
            'total': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # 是否取消下载
        self.cancelled = False
    
    def download_image(self, url: str, save_path: str, 
                      progress_callback: Callable = None) -> str:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
            progress_callback: 进度回调函数
        
        Returns:
            状态字符串: 'skipped'/'success'/'failed'/'error'
        """
        # 检查是否取消
        if self.cancelled:
            return 'failed'
        
        # 如果文件已存在且大小>0，跳过
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            if progress_callback:
                progress_callback('skipped', url, save_path)
            return 'skipped'
        
        for attempt in range(self.retries):
            if self.cancelled:
                return 'failed'
            
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)
                
                if response.status_code == 200:
                    # 确保目录存在
                    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
                    
                    # 直接写入文件
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if self.cancelled:
                                return 'failed'
                            if chunk:
                                f.write(chunk)
                    
                    if progress_callback:
                        progress_callback('success', url, save_path)
                    return 'success'
                
                elif response.status_code == 404:
                    # 404不重试
                    if progress_callback:
                        progress_callback('not_found', url, save_path)
                    return 'failed'
                
            except Exception as e:
                if attempt < self.retries - 1:
                    # 等待后重试
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    if progress_callback:
                        progress_callback('error', url, save_path, str(e))
                    return 'error'
        
        return 'failed'
    
    def download_chapter(self, images: List[str], save_dir: str, 
                        chapter_name: str, progress_callback: Callable = None) -> Dict:
        """
        下载章节
        
        Args:
            images: 图片URL列表
            save_dir: 保存目录
            chapter_name: 章节名称
            progress_callback: 进度回调函数
        
        Returns:
            下载结果统计
        """
        if not images:
            return {'success': 0, 'failed': 0, 'skipped': 0, 'total': 0}
        
        chapter_dir = Path(save_dir) / chapter_name
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        # 章节级别统计（不使用全局self.stats）
        chapter_stats = {'success': 0, 'failed': 0, 'skipped': 0, 'total': len(images)}
        
        # 使用线程池下载
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {}
            
            for idx, img_url in enumerate(images, 1):
                if self.cancelled:
                    break
                
                # 确定文件扩展名
                ext = '.jpg'
                if '.png' in img_url.lower():
                    ext = '.png'
                elif '.webp' in img_url.lower():
                    ext = '.webp'
                
                save_path = chapter_dir / f'{idx:04d}{ext}'
                
                # 提交下载任务
                future = executor.submit(
                    self.download_image, 
                    img_url, 
                    str(save_path), 
                    progress_callback
                )
                futures[future] = (idx, img_url)
            
            # 收集结果
            for future in as_completed(futures):
                if self.cancelled:
                    break
                
                idx, img_url = futures[future]
                try:
                    status = future.result()
                    # 根据返回的状态更新统计
                    if status == 'success':
                        chapter_stats['success'] += 1
                    elif status == 'skipped':
                        chapter_stats['skipped'] += 1
                    else:  # 'failed', 'error'
                        chapter_stats['failed'] += 1
                except Exception as e:
                    chapter_stats['failed'] += 1
                    if progress_callback:
                        progress_callback('error', img_url, '', str(e))
        
        return chapter_stats
    
    def download_manga(self, manga_info: Dict, chapters_to_download: List[int],
                      save_dir: str, progress_callback: Callable = None,
                      chapter_callback: Callable = None) -> Dict:
        """
        下载漫画
        
        Args:
            manga_info: 漫画信息
            chapters_to_download: 要下载的章节索引列表
            save_dir: 保存目录
            progress_callback: 图片下载进度回调
            chapter_callback: 章节完成回调
        
        Returns:
            总体下载结果
        """
        from manga_parser import MangaParser
        
        parser = MangaParser(self.session)
        manga_title = manga_info['title']
        manga_id = manga_info.get('manga_id')
        
        # 如果没有manga_id，尝试从前几个章节检测（避开可能的VIP/JS加载章节）
        if not manga_id and manga_info['chapters']:
            # 尝试前5个章节
            for i in range(min(5, len(manga_info['chapters']))):
                chapter_url = manga_info['chapters'][i]['url']
                detected_id = parser.detect_manga_id_from_chapter(chapter_url)
                if detected_id:
                    manga_id = detected_id
                    break
        
        manga_dir = Path(save_dir) / manga_title
        manga_dir.mkdir(parents=True, exist_ok=True)
        
        total_stats = {
            'total_chapters': len(chapters_to_download),
            'success_chapters': 0,
            'failed_chapters': 0,
            'total_images': 0,
            'success_images': 0,
            'failed_images': 0,
            'skipped_images': 0
        }
        
        # 重置取消标志和统计
        self.cancelled = False
        self.stats = {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        for idx, chapter_idx in enumerate(chapters_to_download, 1):
            if self.cancelled:
                break
            
            if chapter_idx >= len(manga_info['chapters']):
                continue
            
            chapter = manga_info['chapters'][chapter_idx]
            chapter_name = chapter['name']
            chapter_title = chapter.get('title', chapter_name)
            
            if chapter_callback:
                chapter_callback('start', idx, len(chapters_to_download), chapter_title, {})
            
            # 获取章节图片
            images = []
            
            # 优先尝试从页面获取（非VIP章节）
            images = parser.get_chapter_images_from_page(chapter['url'])
            
            # 如果失败，使用URL探测方法（绕过VIP）
            if not images and manga_id:
                images = parser.get_chapter_images(manga_id, chapter_name)
            
            if not images:
                total_stats['failed_chapters'] += 1
                if chapter_callback:
                    chapter_callback('failed', idx, len(chapters_to_download), 
                                   chapter_title, {'error': '无法获取图片'})
                continue
            
            # 下载章节
            chapter_stats = self.download_chapter(
                images, 
                str(manga_dir), 
                chapter_name,
                progress_callback
            )
            
            # 更新统计
            total_stats['total_images'] += chapter_stats['total']
            total_stats['success_images'] += chapter_stats['success']
            total_stats['failed_images'] += chapter_stats['failed']
            total_stats['skipped_images'] += chapter_stats['skipped']
            
            if chapter_stats['success'] > 0:
                total_stats['success_chapters'] += 1
            else:
                total_stats['failed_chapters'] += 1
            
            if chapter_callback:
                chapter_callback('complete', idx, len(chapters_to_download), 
                               chapter_title, chapter_stats)
        
        return total_stats
    
    def cancel(self):
        """取消当前下载"""
        self.cancelled = True
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
    
    def get_stats(self) -> Dict:
        """获取下载统计"""
        return self.stats.copy()

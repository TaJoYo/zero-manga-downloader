#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
下载器核心模块 - 处理漫画下载逻辑
"""

import os
import random
import re
import shutil
import time
import zipfile
import requests
from requests.adapters import HTTPAdapter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Dict, Callable, Optional, Tuple
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from PIL import Image


def sanitize_filename(filename: str) -> str:
    """清理文件名，移除非法字符"""
    if not filename:
        return ""

    cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename).strip()
    if len(cleaned) > 200:
        cleaned = cleaned[:200]
    return cleaned


class MangaDownloader:
    """漫画下载器"""
    
    def __init__(self, threads: int = 15, retries: int = 3, 
                 retry_delay: int = 2, timeout: int = 15,
                 verify_images: bool = True,
                 output_format: str = 'folder'):
        """
        初始化下载器
        
        Args:
            threads: 下载线程数
            retries: 重试次数
            retry_delay: 重试延迟(秒)
            timeout: 请求超时(秒)
            verify_images: 是否严格校验已存在/已下载图片
            output_format: 输出格式（folder/zip/cbz）
        """
        self.threads = threads
        self.retries = retries
        self.retry_delay = retry_delay
        self.timeout_pair = self._normalize_timeout(timeout)
        self.timeout = self.timeout_pair[1]
        self.verify_images = verify_images
        self.output_format = self._normalize_output_format(output_format)
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Referer': 'https://www.zerobywai.com/'
        })
        self._configure_session_pool()
        
        # 下载统计
        self.stats = {
            'total': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # 是否取消下载
        self.cancelled = False

    def _normalize_timeout(self, timeout: int) -> Tuple[float, float]:
        """统一转为 (connect, read) 超时配置"""
        if isinstance(timeout, (tuple, list)) and len(timeout) == 2:
            try:
                connect = max(1.0, float(timeout[0]))
                read = max(1.0, float(timeout[1]))
            except (TypeError, ValueError):
                connect, read = 5.0, 15.0
            return connect, read

        try:
            timeout_value = max(1.0, float(timeout))
        except (TypeError, ValueError):
            timeout_value = 15.0
        connect_timeout = min(10.0, timeout_value)
        return connect_timeout, timeout_value

    def _configure_session_pool(self):
        """为 requests.Session 配置连接池"""
        pool_size = max(10, int(self.threads))
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=0,
            pool_block=True
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def _normalize_output_format(self, output_format: str) -> str:
        """规范输出格式值"""
        normalized = str(output_format).strip().lower()
        if normalized not in {'folder', 'zip', 'cbz'}:
            return 'folder'
        return normalized

    def _is_existing_archive_usable(self, archive_path: Path) -> bool:
        """检查已存在压缩包是否可复用"""
        try:
            return archive_path.exists() and archive_path.is_file() and archive_path.stat().st_size > 0
        except OSError:
            return False

    def _package_chapter_as_archive(self, chapter_dir: Path, archive_path: Path) -> bool:
        """将章节目录打包为 zip/cbz 并删除章节目录"""
        try:
            image_files = sorted([p for p in chapter_dir.iterdir() if p.is_file()])
        except OSError:
            image_files = []

        if not image_files:
            return False

        archive_tmp_path = archive_path.with_name(archive_path.name + '.part')
        self._cleanup_partial_file(str(archive_tmp_path))
        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive_tmp_path, mode='w', compression=zipfile.ZIP_DEFLATED) as zip_file:
                for image_path in image_files:
                    zip_file.write(image_path, arcname=image_path.name)
            os.replace(str(archive_tmp_path), str(archive_path))
            shutil.rmtree(chapter_dir, ignore_errors=True)
            return True
        except Exception:
            self._cleanup_partial_file(str(archive_tmp_path))
            return False

    def _emit_progress(self, progress_callback: Callable, status: str,
                      url: str, save_path: str = '', detail: str = ''):
        """统一发送进度回调"""
        if progress_callback:
            progress_callback(status, url, save_path, detail)

    def _cleanup_partial_file(self, part_path: str):
        """删除临时文件"""
        try:
            if os.path.exists(part_path):
                os.remove(part_path)
        except OSError:
            pass

    def _finalize_download_file(self, part_path: str, save_path: str):
        """将临时文件提交为最终文件，优先原子替换"""
        try:
            os.replace(part_path, save_path)
            return
        except PermissionError:
            # 某些受限环境会拦截 rename，回退到复制后删除
            pass

        with open(part_path, 'rb') as src, open(save_path, 'wb') as dst:
            shutil.copyfileobj(src, dst)
        self._cleanup_partial_file(part_path)

    def _is_image_valid(self, image_path: str) -> bool:
        """检查图片文件是否可读"""
        try:
            if not os.path.exists(image_path):
                return False
            if os.path.getsize(image_path) <= 0:
                return False

            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception:
            return False

    def _is_existing_file_usable(self, save_path: str) -> bool:
        """检查已存在文件是否可复用"""
        if not os.path.exists(save_path):
            return False

        try:
            file_size = os.path.getsize(save_path)
        except OSError:
            return False

        if file_size <= 0:
            return False

        # 轻量模式：仅校验文件大小
        if not self.verify_images:
            return True

        # 严格模式：校验图片可读性
        if self._is_image_valid(save_path):
            return True

        # 校验失败视为损坏文件，删除后重下
        try:
            os.remove(save_path)
        except OSError:
            pass
        return False

    def _parse_retry_after(self, retry_after: str) -> Optional[float]:
        """解析 Retry-After 头"""
        if not retry_after:
            return None

        retry_after = retry_after.strip()
        if not retry_after:
            return None

        # 秒数格式
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass

        # HTTP 日期格式
        try:
            target_time = parsedate_to_datetime(retry_after)
            if target_time.tzinfo is None:
                target_time = target_time.replace(tzinfo=timezone.utc)
            seconds = (target_time - datetime.now(timezone.utc)).total_seconds()
            return max(0.0, seconds)
        except (TypeError, ValueError, OverflowError):
            return None

    def _calc_backoff_delay(self, attempt: int, status_code: Optional[int] = None,
                           retry_after: Optional[str] = None) -> float:
        """根据状态码计算重试等待时间"""
        jitter = random.uniform(0.0, 1.0)
        base_delay = self.retry_delay * (2 ** attempt)

        if status_code == 429:
            retry_after_seconds = self._parse_retry_after(retry_after or '')
            if retry_after_seconds is not None:
                return retry_after_seconds + jitter
            return base_delay + jitter

        if status_code == 403:
            # 403 更保守，避免高频重试
            return max(base_delay * 2, self.retry_delay + 3) + jitter

        if status_code is not None and 500 <= status_code < 600:
            return base_delay + jitter

        return base_delay + jitter
    
    def download_image(self, url: str, save_path: str, 
                      progress_callback: Callable = None) -> str:
        """
        下载单张图片
        
        Args:
            url: 图片URL
            save_path: 保存路径
            progress_callback: 进度回调函数
        
        Returns:
            状态字符串: 'skipped'/'success'/'failed'/'error'/'cancelled'
        """
        # 检查是否取消
        if self.cancelled:
            self._emit_progress(progress_callback, 'cancelled', url, save_path, '下载已取消')
            return 'cancelled'
        
        # 文件完整则跳过
        if self._is_existing_file_usable(save_path):
            self._emit_progress(progress_callback, 'skipped', url, save_path)
            return 'skipped'

        part_path = f"{save_path}.part"
        self._cleanup_partial_file(part_path)

        for attempt in range(max(1, self.retries)):
            if self.cancelled:
                self._cleanup_partial_file(part_path)
                self._emit_progress(progress_callback, 'cancelled', url, save_path, '下载已取消')
                return 'cancelled'
            
            try:
                with self.session.get(url, timeout=self.timeout_pair, stream=True) as response:
                    status_code = response.status_code

                    if status_code == 200:
                        Path(save_path).parent.mkdir(parents=True, exist_ok=True)

                        with open(part_path, 'wb') as tmp_file:
                            for chunk in response.iter_content(chunk_size=8192):
                                if self.cancelled:
                                    self._cleanup_partial_file(part_path)
                                    self._emit_progress(
                                        progress_callback,
                                        'cancelled',
                                        url,
                                        save_path,
                                        '下载已取消'
                                    )
                                    return 'cancelled'
                                if chunk:
                                    tmp_file.write(chunk)

                        if os.path.getsize(part_path) <= 0:
                            raise IOError("下载结果为空文件")

                        self._finalize_download_file(part_path, save_path)

                        # 下载完成后严格校验图片，避免损坏文件残留
                        if self.verify_images and not self._is_image_valid(save_path):
                            try:
                                os.remove(save_path)
                            except OSError:
                                pass

                            if attempt < self.retries - 1:
                                delay = self._calc_backoff_delay(attempt)
                                self._emit_progress(
                                    progress_callback,
                                    'retry',
                                    url,
                                    save_path,
                                    f'图片校验失败，{delay:.1f}s 后重试 ({attempt + 1}/{self.retries})'
                                )
                                time.sleep(delay)
                                continue

                            self._emit_progress(
                                progress_callback,
                                'error',
                                url,
                                save_path,
                                '图片校验失败'
                            )
                            return 'error'

                        self._emit_progress(progress_callback, 'success', url, save_path)
                        return 'success'

                    if status_code == 404:
                        self._cleanup_partial_file(part_path)
                        self._emit_progress(
                            progress_callback,
                            'not_found',
                            url,
                            save_path,
                            'HTTP 404'
                        )
                        return 'failed'

                    if attempt < self.retries - 1:
                        retry_after = response.headers.get('Retry-After')
                        delay = self._calc_backoff_delay(
                            attempt,
                            status_code=status_code,
                            retry_after=retry_after
                        )
                        self._emit_progress(
                            progress_callback,
                            'retry',
                            url,
                            save_path,
                            f'HTTP {status_code}，{delay:.1f}s 后重试 ({attempt + 1}/{self.retries})'
                        )
                        time.sleep(delay)
                        continue

                    self._cleanup_partial_file(part_path)
                    self._emit_progress(
                        progress_callback,
                        'http_error',
                        url,
                        save_path,
                        f'HTTP {status_code}'
                    )
                    return 'failed'

            except requests.RequestException as e:
                self._cleanup_partial_file(part_path)
                if attempt < self.retries - 1:
                    delay = self._calc_backoff_delay(attempt)
                    self._emit_progress(
                        progress_callback,
                        'retry',
                        url,
                        save_path,
                        f'请求异常: {e}，{delay:.1f}s 后重试 ({attempt + 1}/{self.retries})'
                    )
                    time.sleep(delay)
                    continue

                self._emit_progress(progress_callback, 'error', url, save_path, str(e))
                return 'error'
            except Exception as e:
                self._cleanup_partial_file(part_path)
                if attempt < self.retries - 1:
                    delay = self._calc_backoff_delay(attempt)
                    self._emit_progress(
                        progress_callback,
                        'retry',
                        url,
                        save_path,
                        f'下载异常: {e}，{delay:.1f}s 后重试 ({attempt + 1}/{self.retries})'
                    )
                    time.sleep(delay)
                    continue

                self._emit_progress(progress_callback, 'error', url, save_path, str(e))
                return 'error'
        
        self._cleanup_partial_file(part_path)
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
            return {'success': 0, 'failed': 0, 'skipped': 0, 'total': 0, 'cancelled': False}
        safe_chapter_name = sanitize_filename(chapter_name) or "unknown_chapter"
        chapter_dir = Path(save_dir) / safe_chapter_name
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        # 章节级别统计（不使用全局self.stats）
        chapter_stats = {
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'total': len(images),
            'cancelled': False
        }
        executor = ThreadPoolExecutor(max_workers=self.threads)
        futures = {}

        try:
            for idx, img_url in enumerate(images, 1):
                if self.cancelled:
                    chapter_stats['cancelled'] = True
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

            pending = set(futures.keys())
            while pending:
                if self.cancelled:
                    chapter_stats['cancelled'] = True
                    break

                done, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                if not done:
                    continue

                for future in done:
                    idx, img_url = futures[future]
                    try:
                        status = future.result()
                    except Exception as e:
                        chapter_stats['failed'] += 1
                        self._emit_progress(progress_callback, 'error', img_url, '', str(e))
                        continue

                    if status == 'success':
                        chapter_stats['success'] += 1
                    elif status == 'skipped':
                        chapter_stats['skipped'] += 1
                    elif status == 'cancelled':
                        chapter_stats['cancelled'] = True
                    else:
                        chapter_stats['failed'] += 1
        finally:
            if self.cancelled:
                for future in futures:
                    if not future.done():
                        future.cancel()
                executor.shutdown(wait=False, cancel_futures=True)
            else:
                executor.shutdown(wait=True, cancel_futures=False)

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
        
        manga_dir = Path(save_dir) / (sanitize_filename(manga_title) or "未知漫画")
        manga_dir.mkdir(parents=True, exist_ok=True)
        
        total_stats = {
            'total_chapters': len(chapters_to_download),
            'processed_chapters': 0,
            'success_chapters': 0,
            'failed_chapters': 0,
            'planned_images': 0,
            'total_images': 0,
            'success_images': 0,
            'failed_images': 0,
            'skipped_images': 0,
            'cancelled': False,
            'cancelled_chapter': '',
            'elapsed_ms': 0
        }
        
        # 重置取消标志和统计
        self.cancelled = False
        self.stats = {'total': 0, 'downloaded': 0, 'failed': 0, 'skipped': 0}
        
        started_at = time.time()

        for idx, chapter_idx in enumerate(chapters_to_download, 1):
            if self.cancelled:
                total_stats['cancelled'] = True
                break
            
            if chapter_idx >= len(manga_info['chapters']):
                continue
            
            chapter = manga_info['chapters'][chapter_idx]
            chapter_name_raw = chapter.get('name', '')
            chapter_name_safe = sanitize_filename(chapter_name_raw) or f'chapter_{chapter_idx + 1}'
            chapter_title = chapter.get('title', chapter_name_raw) or chapter_name_safe
            chapter_archive_path = None
            if self.output_format in {'zip', 'cbz'}:
                chapter_archive_path = manga_dir / f'{chapter_name_safe}.{self.output_format}'
            total_stats['processed_chapters'] += 1
            
            if chapter_callback:
                chapter_callback(
                    'start',
                    idx,
                    len(chapters_to_download),
                    chapter_title,
                    {'phase': 'downloading'}
                )

            if chapter_archive_path and self._is_existing_archive_usable(chapter_archive_path):
                if chapter_callback:
                    chapter_callback(
                        'info',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {'message': f'已存在章节压缩包，跳过: {chapter_archive_path.name}'}
                    )
                    chapter_callback(
                        'complete',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {
                            'success': 0,
                            'failed': 0,
                            'skipped': 1,
                            'total': 1,
                            'cancelled': False,
                            'phase': 'completed',
                            'archive_path': str(chapter_archive_path)
                        }
                    )
                total_stats['success_chapters'] += 1
                continue
            
            # 获取章节图片
            images = []
            
            # 优先尝试从页面获取（非VIP章节）
            images = parser.get_chapter_images_from_page(chapter['url'])
            
            # 如果失败，使用URL探测方法（绕过VIP）
            if not images and manga_id:
                if chapter_callback:
                    chapter_callback(
                        'info',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {'message': '正在探测VIP图片...', 'phase': 'probing'}
                    )
                images = parser.get_chapter_images(
                    manga_id,
                    chapter_name_raw,
                    max_pages=500,
                    is_cancelled=lambda: self.cancelled,
                    timeout=self.timeout_pair[1],
                    log_callback=(
                        lambda message: chapter_callback(
                            'info',
                            idx,
                            len(chapters_to_download),
                            chapter_title,
                            {'message': message}
                        )
                        if chapter_callback else None
                    )
                )

            if self.cancelled:
                total_stats['cancelled'] = True
                total_stats['cancelled_chapter'] = chapter_title
                if chapter_callback:
                    chapter_callback(
                        'cancelled',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {'phase': 'cancelled'}
                    )
                break
            
            if not images:
                total_stats['failed_chapters'] += 1
                if chapter_callback:
                    chapter_callback(
                        'failed',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {'error': '无法获取图片', 'phase': 'failed'}
                    )
                continue

            total_stats['planned_images'] += len(images)
            if chapter_callback:
                chapter_callback(
                    'images_total',
                    idx,
                    len(chapters_to_download),
                    chapter_title,
                    {
                        'chapter_images': len(images),
                        'planned_images': total_stats['planned_images'],
                        'phase': 'downloading'
                    }
                )
            
            # 下载章节
            chapter_stats = self.download_chapter(
                images, 
                str(manga_dir), 
                chapter_name_safe,
                progress_callback
            )

            if self.output_format in {'zip', 'cbz'} and not chapter_stats.get('cancelled'):
                chapter_dir_path = manga_dir / chapter_name_safe
                chapter_archive_path = manga_dir / f'{chapter_name_safe}.{self.output_format}'
                packaged = self._package_chapter_as_archive(
                    chapter_dir_path,
                    chapter_archive_path
                )
                if packaged:
                    chapter_stats['archive_path'] = str(chapter_archive_path)
                    if chapter_callback:
                        chapter_callback(
                            'info',
                            idx,
                            len(chapters_to_download),
                            chapter_title,
                            {
                                'message': f'章节已打包: {chapter_archive_path.name}',
                                'phase': 'packaging'
                            }
                        )
                else:
                    chapter_stats['package_failed'] = True
                    chapter_stats['error'] = f'章节打包失败: {chapter_archive_path.name}'
            
            # 更新统计
            total_stats['total_images'] += chapter_stats['total']
            total_stats['success_images'] += chapter_stats['success']
            total_stats['failed_images'] += chapter_stats['failed']
            total_stats['skipped_images'] += chapter_stats['skipped']

            if chapter_stats.get('cancelled'):
                total_stats['cancelled'] = True
                total_stats['cancelled_chapter'] = chapter_title
                if chapter_callback:
                    chapter_stats['phase'] = 'cancelled'
                    chapter_callback('cancelled', idx, len(chapters_to_download), chapter_title, chapter_stats)
                break

            if chapter_stats.get('package_failed'):
                total_stats['failed_chapters'] += 1
                if chapter_callback:
                    chapter_callback(
                        'failed',
                        idx,
                        len(chapters_to_download),
                        chapter_title,
                        {'error': chapter_stats.get('error', '章节打包失败'), 'phase': 'failed'}
                    )
                continue
            
            if chapter_stats['success'] > 0 or chapter_stats['skipped'] > 0:
                total_stats['success_chapters'] += 1
            else:
                total_stats['failed_chapters'] += 1
            
            if chapter_callback:
                chapter_stats['phase'] = 'completed'
                chapter_callback('complete', idx, len(chapters_to_download), 
                               chapter_title, chapter_stats)
        
        total_stats['elapsed_ms'] = int((time.time() - started_at) * 1000)
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

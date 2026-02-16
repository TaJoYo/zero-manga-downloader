#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫画解析器 - 支持VIP章节绕过
通过直接访问图片URL绕过VIP限制
"""

import re
import requests
from typing import Callable, Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


class MangaParser:
    """零漫画解析器"""
    
    def __init__(self, session: requests.Session = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.zerobywai.com/'
        })
        self.base_url = 'https://www.zerobywai.com'
        self.image_base_url = 'https://tupa.zerobywai.com/manhua'
    
    def parse_manga_url(self, url: str) -> Optional[Dict]:
        """
        解析漫画主页URL，获取漫画信息
        
        Args:
            url: 漫画主页URL，例如：https://www.zerobywai.com/pc/manga_pc.php?kuid=21019
        
        Returns:
            漫画信息字典，包含title, kuid, manga_id, chapters等
        """
        try:
            # 提取kuid
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            kuid = params.get('kuid', [None])[0]
            
            if not kuid:
                raise ValueError("无法从URL中提取kuid参数")
            
            # 请求页面
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                raise ValueError(f"请求失败，状态码: {response.status_code}")
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取漫画标题
            title = self._extract_title(soup)
            
            # 提取章节列表
            chapters = self._extract_chapters(html)
            
            if not chapters:
                raise ValueError("未找到章节信息")
            
            # 提取漫画ID（用于图片URL）
            manga_id = self._extract_manga_id(html)
            
            # 如果主页面无法提取manga_id（JS加载的情况），尝试从前几个章节获取
            if not manga_id:
                for i in range(min(5, len(chapters))):
                    chapter_url = chapters[i]['url']
                    detected_id = self.detect_manga_id_from_chapter(chapter_url)
                    if detected_id:
                        manga_id = detected_id
                        break
            
            # [调试] 输出manga_id
            
            if not chapters:
                raise ValueError("未找到章节信息")
            
            return {
                'title': title,
                'kuid': kuid,
                'manga_id': manga_id,
                'url': url,
                'chapters': chapters,
                'total_chapters': len(chapters)
            }
            
        except Exception as e:
            raise Exception(f"解析漫画URL失败: {str(e)}")
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取漫画标题"""
        # 尝试多种选择器
        title_selectors = [
            'h1',
            '.manga-title',
            '[class*="title"]',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # 清理标题
                title = re.sub(r'\s*-\s*zero.*', '', title, flags=re.I)
                title = self._sanitize_filename(title)
                if title:
                    return title
        
        return "未知漫画"
    
    def _extract_manga_id(self, html: str) -> Optional[str]:
        """
        提取漫画ID（用于构造图片URL）
        通过分析图片URL来获取
        """
        # 查找图片URL模式
        pattern = r'https?://tupa\.zerobywai\.com/manhua/([A-Za-z0-9]+)/'
        match = re.search(pattern, html)
        

        
        if match:
            return match.group(1)
        
        # 如果在页面中找不到，尝试请求第一个章节来获取
        return None
    
    def _extract_chapters(self, html: str) -> List[Dict]:
        """提取章节列表"""
        chapters = []
        
        # 从JavaScript变量中提取章节数据
        pattern = r'const\s+chapters\s*=\s*(\[.*?\]);'
        match = re.search(pattern, html, re.DOTALL)
        
        if match:
            chapters_json = match.group(1)
            # 提取zjid和zjname
            chapter_pattern =r'{\s*"zjid"\s*:\s*"(\d+)"\s*,\s*"zjname"\s*:\s*"([^"]+)"\s*}'
            
            for match in re.finditer(chapter_pattern, chapters_json):
                zjid = match.group(1)
                zjname = match.group(2)
                
                chapters.append({
                    'zjid': zjid,
                    'name': zjname,
                    'title': f"第{zjname}话" if zjname.isdigit() else zjname,
                    'url': f'{self.base_url}/pc/manga_read_pc.php?zjid={zjid}'
                })
        
        return chapters
    
    def _probe_image_exists(self, url: str, timeout: int = 10) -> Optional[bool]:
        """
        探测图片URL是否存在

        Returns:
            True: 存在
            False: 不存在(404)
            None: 状态不确定(网络错误/限流等)
        """
        # 优先HEAD，成本更低
        try:
            response = self.session.head(url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                return True
            if response.status_code == 404:
                return False

            # HEAD受限时降级到 GET + Range
            if response.status_code in (403, 405):
                pass
            else:
                return None
        except requests.RequestException:
            pass

        # 部分CDN/站点会拒绝HEAD，这里降级做轻量GET
        try:
            response = self.session.get(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={'Range': 'bytes=0-0'},
                stream=True
            )
            if response.status_code in (200, 206):
                return True
            if response.status_code == 404:
                return False
            return None
        except requests.RequestException:
            return None

    def _detect_pattern_for_first_page(
        self,
        manga_id: str,
        chapter_name: str,
        formats: List[str],
        timeout: int = 10,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Optional[Tuple[int, str, int]]:
        """探测首个可用规则: (padding_width, ext, first_page)"""
        page_format_widths = [3, 2, 1]

        # 正常从第1页开始，最多前3页兜底探测，避免某些章节首图偏移
        for page_num in (1, 2, 3):
            for ext in formats:
                for width in page_format_widths:
                    if is_cancelled and is_cancelled():
                        return None

                    page_str = str(page_num) if width == 1 else f"{page_num:0{width}d}"
                    url = f"{self.image_base_url}/{manga_id}/{chapter_name}/{page_str}{ext}"
                    exists = self._probe_image_exists(url, timeout=timeout)
                    if exists is True:
                        return width, ext, page_num

        return None

    def get_chapter_images(self, manga_id: str, chapter_name: str, 
                          max_pages: int = 500, formats: List[str] = None,
                          verbose: bool = False,
                          is_cancelled: Optional[Callable[[], bool]] = None,
                          timeout: int = 10,
                          log_callback: Optional[Callable[[str], None]] = None) -> List[str]:
        """
        获取章节的所有图片URL（绕过VIP限制）
        
        Args:
            manga_id: 漫画ID
            chapter_name: 章节名称（用于构造URL）
            max_pages: 最大页数
            formats: 图片格式列表，默认为['.jpg', '.png']
            verbose: 是否输出详细日志
            is_cancelled: 取消检查回调
            timeout: 探测超时
            log_callback: 探测日志回调
        
        Returns:
            图片URL列表
        """
        if formats is None:
            formats = ['.jpg', '.png']

        def emit_log(message: str):
            if verbose:
                print(message)
            if log_callback:
                log_callback(message)

        emit_log(f"  [探测] 章节: {chapter_name}, manga_id: {manga_id}")

        if is_cancelled and is_cancelled():
            emit_log("  [探测] 用户取消探测")
            return []

        # 先锁定规则，避免每页进行笛卡尔积尝试
        pattern = self._detect_pattern_for_first_page(
            manga_id=manga_id,
            chapter_name=chapter_name,
            formats=formats,
            timeout=timeout,
            is_cancelled=is_cancelled
        )

        if not pattern:
            emit_log("  [探测] 未能锁定可用规则，探测结束")
            return []

        page_width, ext, first_page = pattern
        current_ext = ext
        sample_page = "1" if page_width == 1 else f"{1:0{page_width}d}"
        emit_log(f"  [探测] 已锁定规则: {sample_page} + {current_ext}")

        images = []
        consecutive_failures = 0
        max_consecutive_failures = 3

        # 从第1页扫描，保证不漏掉前置页
        for page_num in range(1, max_pages + 1):
            if is_cancelled and is_cancelled():
                emit_log("  [探测] 用户取消探测")
                break

            page_str = str(page_num) if page_width == 1 else f"{page_num:0{page_width}d}"
            # 每页优先当前后缀，失败再尝试其他后缀，避免章节中途后缀切换漏页
            ext_candidates = [current_ext] + [candidate for candidate in formats if candidate != current_ext]
            found = False

            for candidate_ext in ext_candidates:
                url = f"{self.image_base_url}/{manga_id}/{chapter_name}/{page_str}{candidate_ext}"
                exists = self._probe_image_exists(url, timeout=timeout)
                if exists is True:
                    images.append(url)
                    if candidate_ext != current_ext:
                        emit_log(f"  [探测] 第{page_num}页后缀切换: {current_ext} -> {candidate_ext}")
                        current_ext = candidate_ext
                    consecutive_failures = 0
                    found = True
                    break

            if found:
                if page_num % 20 == 0:
                    emit_log(f"  [探测] 已找到 {len(images)} 张图片...")
                continue

            consecutive_failures += 1
            if consecutive_failures >= max_consecutive_failures and page_num >= first_page:
                emit_log(f"  [探测] 连续{max_consecutive_failures}次失败，探测结束")
                break

        emit_log(f"  [探测] 完成，共找到 {len(images)} 张图片")
        return images
    
    def get_chapter_images_from_page(self, chapter_url: str) -> List[str]:
        """
        从章节阅读页面提取图片URL（适用于非VIP章节）
        
        Args:
            chapter_url: 章节阅读页面URL
        
        Returns:
            图片URL列表
        """
        try:
            response = self.session.get(chapter_url, timeout=15)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return []
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            # 检查是否是VIP章节
            if 'VIP 专属章节' in html or 'vip' in html.lower():
                return []
            
            images = []
            
            # 查找所有图片
            img_tags = soup.find_all('img')
            for img in img_tags:
                src = img.get('src') or img.get('data-src')
                if src and 'manhua' in src:
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://tupa.zerobywai.com' + src
                    
                    if src not in images:
                        images.append(src)
            
            # 排序图片
            images.sort(key=lambda x: self._extract_page_number(x))
            
            return images
            
        except Exception:
            return []
    
    def _extract_page_number(self, url: str) -> int:
        """从图片URL中提取页码"""
        match = re.search(r'/(\d+)\.(jpg|png)$', url)
        if match:
            return int(match.group(1))
        return 0
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除非法字符"""
        # 移除Windows文件名非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        filename = re.sub(illegal_chars, '_', filename)
        # 移除前后空格
        filename = filename.strip()
        # 限制长度
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def detect_manga_id_from_chapter(self, chapter_url: str) -> Optional[str]:
        """
        从章节页面检测漫画ID
        
        Args:
            chapter_url: 章节URL
        
        Returns:
            漫画ID
        """
        try:
            response = self.session.get(chapter_url, timeout=15)
            response.encoding = 'utf-8'
            
            # 从图片URL中提取manga_id
            pattern = r'https?://tupa\.zerobywai\.com/manhua/([A-Za-z0-9]+)/'
            match = re.search(pattern, response.text)
            
            if match:
                return match.group(1)
            
            return None
            
        except:
            return None

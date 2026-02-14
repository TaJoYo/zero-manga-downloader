#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
漫画解析器 - 支持VIP章节绕过
通过直接访问图片URL绕过VIP限制
"""

import re
import requests
from typing import Dict, List, Optional
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
    
    def get_chapter_images(self, manga_id: str, chapter_name: str, 
                          max_pages: int = 500, formats: List[str] = None,
                          verbose: bool = False) -> List[str]:
        """
        获取章节的所有图片URL（绕过VIP限制）
        
        Args:
            manga_id: 漫画ID
            chapter_name: 章节名称（用于构造URL）
            max_pages: 最大页数
            formats: 图片格式列表，默认为['.jpg', '.png']
            verbose: 是否输出详细日志
        
        Returns:
            图片URL列表
        """
        if formats is None:
            formats = ['.jpg', '.png']
        
        if verbose:
            print(f"  [探测] 章节: {chapter_name}, manga_id: {manga_id}")
        
        images = []
        consecutive_errors = 0
        max_errors = 5  # 连续5个404就认为章节结束
        
        for page_num in range(1, max_pages + 1):
            found = False
            
            # 尝试多种页码格式
            page_formats = [
                f"{page_num:03d}",  # 001, 002... (3位数字)
                f"{page_num:02d}",  # 01, 02... (2位数字)
                f"{page_num}",      # 1, 2... (无补零)
            ]
            
            # 尝试不同的图片格式
            for fmt in formats:
                for page_str in page_formats:
                    url = f"{self.image_base_url}/{manga_id}/{chapter_name}/{page_str}{fmt}"
                    
                    try:
                        # 使用HEAD请求检查图片是否存在
                        response = self.session.head(url, timeout=10, allow_redirects=True)
                        
                        if response.status_code == 200:
                            images.append(url)
                            consecutive_errors = 0
                            found = True
                            if verbose and page_num % 20 == 0:
                                print(f"  [探测] 已找到 {page_num} 页...")
                            break
                    
                    except:
                        pass
                
                # 如果找到，就不用尝试其他格式了
                if found:
                    break
            
            if not found:
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    if verbose:
                        print(f"  [探测] 连续{max_errors}个404，探测结束")
                    break
        
        if verbose:
            print(f"  [探测] 完成，共找到 {len(images)} 张图片")
        
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

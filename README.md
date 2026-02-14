# 零漫画下载器

一个功能强大的漫画下载工具，支持从零漫画网站下载漫画。

采用现代化的Fluent Design风格PyQt5图形界面，简洁易用。

## ✨ 主要特性

- 💎 **Fluent Design风格** - 采用微软Fluent设计语言，界面风格现代简洁
- 🖥️ **PyQt5图形界面** - 功能完整的桌面应用程序
- ⚡ **多线程下载** - 支持最多50个并发下载线程
- 🔄 **智能重试机制** - 自动重试失败的下载
- 📝 **历史记录管理** - 自动保存下载历史
- ⚙️ **灵活的配置** - 可自定义下载参数

##  安装

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd zero-manga-downloader
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包括：
- `requests` - HTTP请求
- `beautifulsoup4` - HTML解析
- `PyQt5` - GUI界面
- `PyQt5-Fluent-Widgets` - Fluent Design风格组件
- `lxml` - XML/HTML解析器
- `Pillow` - 图片处理

## 🎮 使用方法

### Web版本（推荐） ⭐

**最现代化、最好用的方式！**

运行Web服务器：

```bash
python gui_downloader_fluent.py
```

或者双击 `启动下载器_Fluent.bat`（Windows）

程序启动后会显示GUI界面。

**功能：**

- 💫 Fluent Design风格，界面现代简洁
- 支持实时进度显示
- 智能章节选择（全选、清除、部分选择）
- 灵活的线程调整
- 下载历史记录
- 配置管理

### GUI版本

运行GUI程序：

```bash
python gui_downloader_fluent.py
```

使用步骤：

1. **输入漫画URL** - 在主界面输入漫画地址，例如：
   ```
   https://www.zerobywai.com/pc/manga_pc.php?kuid=21019
   ```

2. **点击"解析"** - 程序会自动解析漫画信息，识别所有章节

3. **选择章节** - 勾选要下载的章节，支持全选和部分选择

4. **开始下载** - 点击"开始下载"按钮，程序会自动：
   - 探测每个章节的图片数量
   - 多线程并发下载
   - 自动重试失败的下载
   - 实时显示下载进度

5. **配置设置** - 在"设置"页面可以调整：
   - 下载线程数（1-50）
   - 重试次数（1-10）
   - 重试延迟（0-60秒）
   - 下载目录
   - 历史记录管理

### 命令行版本

运行命令行程序：

```bash
python downloader.py
```

按照提示输入URL和选择章节即可。

## 📁 项目结构

```
zero-manga-downloader/
├── gui_downloader_fluent.py   # GUI主程序（Fluent Design）
├── manga_parser.py            # 漫画解析器
├── downloader.py              # 下载器核心
├── config_manager.py          # 配置管理
├── history_manager.py         # 历史记录管理
├── 启动下载器_Fluent.bat      # Windows启动脚本
├── requirements.txt           # 依赖包列表
├── 使用指南.md               # 详细使用教程
└── README.md                  # 本文件
```

## ⚙️ 配置说明

配置文件位置：`~/.zero_manga_config.json`

默认配置：

```json
{
  "account": {
    "username": "",
    "password": "",
    "cookies": {}
  },
  "download": {
    "threads": 15,
    "retries": 3,
    "retry_delay": 2,
    "download_dir": "~/Downloads",
    "timeout": 15
  },
  "history": {
    "enabled": true,
    "max_records": 100
  }
}
```

## 📝 历史记录

历史记录文件位置：`~/.zero_manga_history.json`

记录包含：
- 漫画URL和标题
- 章节数量
- 下载状态（完成/失败/部分完成）
- 首次和最后下载时间
- 下载次数

## 🔧 开发说明

### 核心模块

1. **manga_parser.py** - 漫画解析器
   - `parse_manga_url()` - 解析漫画主页
   - `get_chapter_images()` - 获取章节图片

2. **downloader.py** - 下载器
   - `download_image()` - 下载单张图片
   - `download_chapter()` - 下载章节
   - `download_manga()` - 下载整部漫画

3. **config_manager.py** - 配置管理
   - 支持读写配置
   - 提供便捷的get/set方法

4. **history_manager.py** - 历史记录
   - 添加/删除/搜索记录
   - 统计信息

### 扩展开发

如需添加新功能：

1. 添加新的解析方法到 `manga_parser.py`
2. 在 `downloader.py` 中实现下载逻辑
3. 在 `gui_downloader.py` 中添加UI控件

## ⚠️ 免责声明

本工具仅供学习和研究使用。使用本工具下载漫画时：

1. 请尊重版权，支持正版
2. 不要用于商业用途
3. 建议适度使用，避免对服务器造成过大压力
4. 使用本工具产生的任何后果由使用者自行承担

## 🐛 问题反馈

如遇到问题，请检查：

1. Python版本是否为3.7+
2. 依赖包是否正确安装
3. 网络连接是否正常
4. 漫画URL格式是否正确

## 📄 许可证

本项目仅供学习交流使用。

## 🤖 关于本项目

**本项目代码由AI编写，基于用户指导开发。** 这是一个展示AI在软件开发中能力的示例项目。

## 🙏 致谢

- 感谢 [Bear-biscuit/Zero_download](https://github.com/Bear-biscuit/Zero_download) 项目提供的参考和灵感
- 感谢零漫画网站提供的漫画资源

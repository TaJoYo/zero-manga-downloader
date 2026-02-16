# 零漫画下载器

一个功能强大的漫画下载工具，支持从零漫画网站下载漫画。

采用现代化的Fluent Design风格PyQt5图形界面，简洁易用。

## ✨ 主要特性

- 💎 **Fluent Design风格** - 采用微软Fluent设计语言，界面风格现代简洁
- 🖥️ **PyQt5图形界面** - 功能完整的桌面应用程序
- ⚡ **多线程下载** - 支持最多50个并发下载线程
- 🔄 **智能重试机制** - 自动重试失败的下载
- 🧭 **图片格式自适应** - 支持多种图片格式自动识别，提高下载成功率
- 📝 **历史记录管理** - 自动保存下载历史
- ⚙️ **灵活的配置** - 可自定义下载参数

##  安装

### 1. 克隆或下载项目

```bash
git clone <repository-url>
cd zero-manga-downloader
```

### 2. 安装依赖

**Windows用户（推荐）：**
- 双击 `install_requirements.bat` 自动安装依赖

**或使用命令行：**
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

### GUI版本

运行GUI程序，有两种方式：

**方式1：双击启动脚本（推荐）**
- Windows用户可直接双击 `启动下载器_Fluent.bat` 文件启动

**方式2：命令行启动**
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
   - 会员章节自动处理 `jpg/png` 后缀切换
   - 多线程并发下载
   - 自动重试失败的下载
   - 实时显示下载进度

5. **配置设置** - 在"设置"页面可以调整：
   - 下载线程数（1-50）
   - 重试次数（1-10）
   - 重试延迟（0-60秒）
   - 请求超时（3-120秒）
   - 输出格式（章节文件夹 / ZIP / CBZ）
   - 严格校验已存在图片（损坏自动重下）
   - 下载目录
   - 历史记录管理

> 当前版本仅提供 GUI 入口。`downloader.py` 是下载核心模块，不是独立命令行程序。

## 📁 项目结构

```
zero-manga-downloader/
├── gui_downloader_fluent.py   # GUI主程序（Fluent Design）
├── manga_parser.py            # 漫画解析器
├── downloader.py              # 下载器核心
├── config_manager.py          # 配置管理
├── history_manager.py         # 历史记录管理
├── install_requirements.bat    # 依赖安装脚本（首次运行）
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
  "download": {
    "threads": 15,
    "retries": 3,
    "retry_delay": 2,
    "download_dir": "~/Downloads",
    "timeout": 15,
    "verify_images": true,
    "output_format": "folder"
  },
  "ui": {
    "language": "zh-CN",
    "window_size": [900, 700],
    "window_position": null,
    "font_size": 10
  },
  "history": {
    "enabled": true,
    "max_records": 100
  }
}
```

`output_format` 说明：
- `folder`：每章为一个文件夹（当前默认行为）
- `zip`：每章输出为 `.zip` 压缩包
- `cbz`：每章输出为 `.cbz`（与 zip 内容相同，仅后缀不同）

当使用 `zip/cbz` 时，目录结构为：
```text
下载目录/
└── 漫画名称/
    ├── 第1话.zip/.cbz
    ├── 第2话.zip/.cbz
    └── ...
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

# AgentCBR - 网页内容自动抓取分析系统

## 功能特性

- 图形化界面，可视化操作
- 自动登录网站并抓取列表数据
- 支持PDF、Word、Excel、图片等多种附件格式
- OCR图片识别（中英文）
- 结构化输出到Word文档
- 断点续传功能
- 自动重新登录

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行

### GUI界面版本
```bash
python src/gui.py
```

### 命令行版本
```bash
python src/main.py
```

## 打包为exe

```bash
pip install pyinstaller
python build.py
```

生成的exe文件在 `dist/AgentCBR.exe`，双击即可运行图形界面

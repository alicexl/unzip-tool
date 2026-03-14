# 压缩包解压工具

自动解压 zip/rar 文件到同名目录，解压成功后删除压缩包。

## 安装

```bash
pip install -r requirements.txt
```

> 注意: RAR 格式需要系统安装 UnRAR 或 7-Zip

## 使用

```bash
# 基本使用（解压后删除压缩包）
python run.py <目录>

# 解压后保留压缩包
python run.py <目录> -k
python run.py <目录> --keep

# 示例
python run.py D:/downloads
python run.py "D:/我的文件" -k
```

## 功能

- **同名目录**: 解压到与压缩包同名的目录
- **自动删除**: 解压成功后自动删除压缩包
- **串行处理**: 逐个解压，稳定可靠
- **跳过已存在**: 目标目录已存在时自动跳过

## 支持格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| ZIP | `.zip` | Python 内置支持 |
| RAR | `.rar` | 需要 rarfile 库 + UnRAR |
| 7z | `.7z` | 需要 py7zr 库 |

## 示例

```
目录结构:
downloads/
├── photo.zip
└── video.rar

执行后:
downloads/
├── photo/
│   └── ... (解压内容)
└── video/
    └── ... (解压内容)
```

## 参数

| 参数 | 说明 |
|------|------|
| `<目录>` | 包含压缩包的目录 |
| `-k, --keep` | 解压后保留压缩包 |

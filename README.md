# 压缩包解压工具

自动解压 zip/rar/7z 文件到同名目录，解压成功后删除压缩包。

## 安装

```bash
pip install -r requirements.txt
```

> 注意: RAR 格式需要系统安装 UnRAR 或 7-Zip

## 使用

```bash
# 基本使用（递归搜索子目录，解压后删除压缩包）
python run.py <目录>

# 解压后保留压缩包
python run.py <目录> -k
python run.py <目录> --keep

# 解压带密码的压缩包
python run.py <目录> -w <密码>
python run.py <目录> --password <密码>

# 仅搜索当前目录（不递归）
python run.py <目录> --no-recursive

# 示例
python run.py D:/downloads
python run.py "D:/我的文件" -k
python run.py D:/downloads -w mypassword
```

## 功能

- **递归搜索**: 自动搜索所有子目录中的压缩包
- **同名目录**: 解压到与压缩包同名的目录
- **自动删除**: 解压成功后自动删除压缩包
- **密码支持**: 支持解压带密码的压缩包
- **进度显示**: 实时显示解压进度
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
├── subdir/
│   └── video.rar
└── deep/
    └── nested/
        └── data.7z

执行后:
downloads/
├── photo/
│   └── ... (解压内容)
├── subdir/
│   └── video/
│       └── ... (解压内容)
└── deep/
    └── nested/
        └── data/
            └── ... (解压内容)
```

## 参数

| 参数 | 说明 |
|------|------|
| `<目录>` | 包含压缩包的目录 |
| `-k, --keep` | 解压后保留压缩包 |
| `-w, --password` | 解压密码 |
| `--no-recursive` | 不递归搜索子目录 |

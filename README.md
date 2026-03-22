# 压缩包解压工具

递归搜索并解压 zip/rar/7z/tar 文件，支持嵌套压缩包智能处理，解压成功后删除压缩包。

## 安装

```bash
pip install -r requirements.txt
```

> 注意:
> - RAR 格式需要系统安装 UnRAR 或 7-Zip
> - 分卷 7z 文件需要 7-Zip

## 使用

```bash
# 基本使用（递归搜索，解压后删除压缩包）
python run.py <目录>

# 解压带密码的压缩包
python run.py <目录> -w <密码>
python run.py <目录> --password <密码>

# 示例
python run.py D:/downloads
python run.py D:/downloads -w mypassword
```

## 功能

- **递归搜索**: 自动搜索所有子目录中的压缩包
- **分卷支持**: 支持 7z/zip/rar 分卷压缩包（如 `.7z.001`, `.zip.001`）
- **递归解压**: 解压后发现嵌套压缩包自动追加处理
- **智能目录**: 单目录结构使用内部目录名，多文件使用压缩包同名目录
- **嵌套优化**: 内层压缩包直接放到父目录，不创建额外子目录
- **目录名清理**: 移除中括号内容、空格转下划线、中文标点转英文
- **自动删除**: 解压成功后自动删除压缩包
- **密码支持**: 支持解压带密码的压缩包
- **进度显示**: 实时显示解压进度
- **跳过已存在**: 目标目录已存在时自动跳过

## 支持格式

| 格式 | 扩展名 | 分卷 | 说明 |
|------|--------|------|------|
| ZIP | `.zip` | `.zip.001` | Python 内置支持 |
| RAR | `.rar` | `.rar.001` | 需要 rarfile 库 + UnRAR |
| 7z | `.7z` | `.7z.001` | 需要 py7zr 或 7-Zip |
| TAR | `.tar` | - | Python 内置支持 (含 .tar.gz/.tar.bz2/.tar.xz) |

## 示例

```
目录结构:
downloads/
├── photo.zip
├── video.7z.001    ← 分卷首卷
├── video.7z.002
├── video.7z.003
└── subdir/
    └── data.rar

执行 python run.py downloads 后:
downloads/
├── photo/           ← 解压内容
├── video/           ← 分卷解压内容
└── subdir/
    └── data/        ← 解压内容
```

### 嵌套压缩包示例

```
原始结构:
006/
└── 006.7z           ← 内含 xxx.rar

执行后:
006/
└── xxx/             ← rar 内容直接在 006/ 下
```

## 参数

| 参数 | 说明 |
|------|------|
| `<目录>` | 包含压缩包的目录 |
| `-w, --password` | 解压密码 |

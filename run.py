#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
压缩包解压工具
自动解压 zip/rar/7z 文件到同名目录，解压成功后删除压缩包
"""

import click
import logging
from pathlib import Path
from datetime import datetime

from src.extractor import ArchiveExtractor


def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        console = logging.StreamHandler()
        console.setLevel(getattr(logging, level.upper()))
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger


@click.command()
@click.argument('directory', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-k', '--keep',
    is_flag=True,
    default=False,
    help='解压后保留压缩包（不删除）'
)
@click.option(
    '-w', '--password',
    default=None,
    help='解压密码'
)
def extract(directory: Path, keep: bool, password: str):
    """
    解压压缩包到同名目录

    DIRECTORY: 包含压缩包的目录
    """
    directory = directory.resolve()

    logger = setup_logger('unzip_tool')
    delete_after = not keep

    print(f"\n压缩包解压工具")
    print(f"{'=' * 40}")
    print(f"目录: {directory}")
    print(f"解压后: {'保留' if keep else '删除'}压缩包")
    if password:
        print(f"密码: {'*' * len(password)}")
    print(f"{'=' * 40}\n")

    # 初始化解压器
    extractor = ArchiveExtractor(delete_after_extract=delete_after, password=password)

    # 扫描压缩包
    archives = extractor.scan_archives(directory)

    if not archives:
        print("未找到压缩包文件")
        return

    # 显示扫描结果
    print(f"发现 {len(archives)} 个压缩包:\n")
    for arc in archives:
        size_mb = arc.stat().st_size / (1024 * 1024)
        print(f"  - {arc.name} ({size_mb:.1f} MB)")

    # 用户确认
    print(f"\n即将解压到同名目录")
    if not keep:
        print("解压成功后将删除压缩包")

    if not click.confirm("\n确认开始", default=True):
        print("已取消")
        return

    # 开始解压
    start_time = datetime.now()
    print(f"\n开始解压...\n")

    def show_progress(current, total, name, result):
        status = result['status']
        if status == 'success':
            symbol = '✓'
        elif status == 'skipped':
            symbol = '→'
        else:
            symbol = '✗'
        print(f"  [{current}/{total}] {symbol} {name} - {result['message']}")

    stats = extractor.extract_all(archives, progress_callback=show_progress)

    # 显示结果
    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 40}")
    print(f"处理完成")
    print(f"  - 总计: {stats['total']}")
    print(f"  - 成功: {stats['success']}")
    print(f"  - 跳过: {stats['skipped']}")
    print(f"  - 失败: {stats['failed']}")
    if not keep:
        print(f"  - 已删除: {stats['deleted']}")
    print(f"用时: {elapsed}")
    print(f"{'=' * 40}")


if __name__ == '__main__':
    extract()

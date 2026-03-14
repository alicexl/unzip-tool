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
    解压压缩包到同名目录（递归搜索子目录）

    DIRECTORY: 包含压缩包的目录
    """
    directory = directory.resolve()

    logger = setup_logger('unzip_tool')
    delete_after = not keep

    print(f"\n压缩包解压工具")
    print(f"{'=' * 40}")
    print(f"目录: {directory}")
    print(f"模式: 递归搜索子目录")
    print(f"解压后: {'保留' if keep else '删除'}压缩包")
    if password:
        print(f"密码: {'*' * len(password)}")
    print(f"{'=' * 40}\n")

    # 初始化解压器
    extractor = ArchiveExtractor(delete_after_extract=delete_after, password=password)

    # 扫描压缩包（仅扫描一次，以初始列表为准）
    archives = extractor.scan_archives(directory)

    if not archives:
        print("未找到压缩包文件")
        return

    # 显示扫描结果
    print(f"发现 {len(archives)} 个压缩包:\n")
    for arc in archives:
        size_mb = arc.stat().st_size / (1024 * 1024)
        display_path = str(arc.relative_to(directory))
        print(f"  - {display_path} ({size_mb:.1f} MB)")

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

    def show_file_progress(archive_name, file_current, file_total, filename):
        """显示文件级进度"""
        # 截断过长的文件名
        display_name = filename if len(filename) <= 40 else "..." + filename[-37:]
        # 显示相对路径
        rel_path = archive_name
        if len(rel_path) > 30:
            rel_path = "..." + rel_path[-27:]
        print(f"\r    {rel_path}: [{file_current}/{file_total}] {display_name}", end="", flush=True)

    def show_progress(current, total, name, result):
        """显示压缩包级进度"""
        # 先清空当前行（如果有文件进度的话）
        print("\r" + " " * 100 + "\r", end="")

        status = result['status']
        if status == 'success':
            symbol = '[OK]'
        elif status == 'skipped':
            symbol = '[SKIP]'
        else:
            symbol = '[FAIL]'

        # 显示相对路径
        display_name = str(name.relative_to(directory))
        print(f"  [{current}/{total}] {symbol} {display_name} - {result['message']}")

    stats = extractor.extract_all(
        archives,
        progress_callback=show_progress,
        file_progress_callback=show_file_progress
    )

    # 显示结果
    elapsed = datetime.now() - start_time
    print(f"\n{'=' * 40}")
    print(f"处理完成")
    print(f"  - 初始任务: {stats['initial']}")
    if stats['discovered'] > 0:
        print(f"  - 递归发现: {stats['discovered']}")
    print(f"  - 成功: {stats['success']}")
    print(f"  - 跳过: {stats['skipped']}")
    print(f"  - 失败: {stats['failed']}")
    if not keep:
        print(f"  - 已删除: {stats['deleted']}")
    print(f"用时: {elapsed}")
    print(f"{'=' * 40}")


if __name__ == '__main__':
    extract()

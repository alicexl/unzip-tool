# -*- coding: utf-8 -*-
"""
压缩包解压模块
支持 zip, rar, 7z 格式
"""

import zipfile
import logging
from pathlib import Path
from typing import Tuple, List, Optional

try:
    import rarfile
    RAR_SUPPORTED = True
except ImportError:
    RAR_SUPPORTED = False

try:
    import py7zr
    SEVENZ_SUPPORTED = True
except ImportError:
    SEVENZ_SUPPORTED = False

logger = logging.getLogger(__name__)

# 支持的压缩包扩展名
ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z'}


class ArchiveExtractor:
    """压缩包解压器"""

    def __init__(self, delete_after_extract: bool = True, password: str = None):
        """
        初始化解压器

        Args:
            delete_after_extract: 解压成功后是否删除压缩包
            password: 解压密码
        """
        self.delete_after_extract = delete_after_extract
        self.password = password

        if not RAR_SUPPORTED:
            logger.warning("rarfile 未安装，RAR 格式将无法处理")
        if not SEVENZ_SUPPORTED:
            logger.warning("py7zr 未安装，7z 格式将无法处理")

    def is_archive(self, file_path: Path) -> bool:
        """检查文件是否是支持的压缩包"""
        return file_path.suffix.lower() in ARCHIVE_EXTENSIONS

    def scan_archives(self, directory: Path) -> List[Path]:
        """
        扫描目录中的压缩包文件

        Args:
            directory: 目录路径

        Returns:
            压缩包文件列表
        """
        directory = directory.resolve()
        archives = []

        for file_path in directory.iterdir():
            if file_path.is_file() and self.is_archive(file_path):
                archives.append(file_path)
                logger.debug(f"发现压缩包: {file_path.name}")

        logger.info(f"扫描完成: 发现 {len(archives)} 个压缩包")
        return sorted(archives)

    def get_extract_dir(self, archive_path: Path) -> Path:
        """
        获取解压目标目录（同名目录）

        Args:
            archive_path: 压缩包路径

        Returns:
            解压目标目录
        """
        # 去掉扩展名作为目录名
        name_without_ext = archive_path.stem
        return archive_path.parent / name_without_ext

    def extract_zip(self, archive_path: Path, extract_dir: Path) -> Tuple[bool, str]:
        """
        解压 ZIP 文件

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录

        Returns:
            (是否成功, 消息)
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # 检查是否是有效的 ZIP 文件
                bad_file = zf.testzip()
                if bad_file is not None:
                    return False, f"ZIP 文件损坏: {bad_file}"

                # 检查是否需要密码
                pwd = self.password.encode() if self.password else None
                zf.extractall(extract_dir, pwd=pwd)

            return True, "解压成功"

        except RuntimeError as e:
            if 'password' in str(e).lower() or 'encrypted' in str(e).lower():
                return False, "需要密码或密码错误"
            return False, f"解压失败: {e}"
        except zipfile.BadZipFile as e:
            return False, f"无效的 ZIP 文件: {e}"
        except Exception as e:
            return False, f"解压失败: {e}"

    def extract_rar(self, archive_path: Path, extract_dir: Path) -> Tuple[bool, str]:
        """
        解压 RAR 文件

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录

        Returns:
            (是否成功, 消息)
        """
        if not RAR_SUPPORTED:
            return False, "rarfile 库未安装，无法处理 RAR 文件"

        try:
            with rarfile.RarFile(archive_path, 'r') as rf:
                rf.extractall(extract_dir, pwd=self.password)

            return True, "解压成功"

        except rarfile.PasswordRequired:
            return False, "需要密码或密码错误"
        except rarfile.BadRarFile as e:
            return False, f"无效的 RAR 文件: {e}"
        except rarfile.NeedFirstVolume:
            return False, "需要 RAR 分卷的第一个文件"
        except Exception as e:
            return False, f"解压失败: {e}"

    def extract_7z(self, archive_path: Path, extract_dir: Path) -> Tuple[bool, str]:
        """
        解压 7z 文件

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录

        Returns:
            (是否成功, 消息)
        """
        if not SEVENZ_SUPPORTED:
            return False, "py7zr 库未安装，无法处理 7z 文件"

        try:
            with py7zr.SevenZipFile(archive_path, 'r', password=self.password) as szf:
                szf.extractall(extract_dir)

            return True, "解压成功"

        except py7zr.exceptions.PasswordRequired:
            return False, "需要密码或密码错误"
        except py7zr.exceptions.Bad7zFile as e:
            return False, f"无效的 7z 文件: {e}"
        except Exception as e:
            if 'password' in str(e).lower():
                return False, "需要密码或密码错误"
            return False, f"解压失败: {e}"

    def extract(self, archive_path: Path) -> dict:
        """
        解压单个压缩包

        Args:
            archive_path: 压缩包路径

        Returns:
            结果字典
        """
        archive_path = archive_path.resolve()
        extract_dir = self.get_extract_dir(archive_path)

        result = {
            'archive': archive_path,
            'extract_dir': extract_dir,
            'status': 'failed',
            'message': '',
            'deleted': False
        }

        # 检查目标目录是否已存在
        if extract_dir.exists():
            result['message'] = f"目标目录已存在: {extract_dir.name}"
            logger.warning(f"跳过 {archive_path.name}: 目标目录已存在")
            result['status'] = 'skipped'
            return result

        # 创建目标目录
        try:
            extract_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            result['message'] = f"创建目录失败: {e}"
            logger.error(f"创建目录失败 {extract_dir}: {e}")
            return result

        # 根据扩展名选择解压方法
        ext = archive_path.suffix.lower()
        if ext == '.zip':
            success, message = self.extract_zip(archive_path, extract_dir)
        elif ext == '.rar':
            success, message = self.extract_rar(archive_path, extract_dir)
        elif ext == '.7z':
            success, message = self.extract_7z(archive_path, extract_dir)
        else:
            result['message'] = f"不支持的格式: {ext}"
            return result

        if success:
            result['status'] = 'success'
            result['message'] = message
            logger.info(f"解压成功: {archive_path.name} -> {extract_dir.name}")

            # 删除压缩包
            if self.delete_after_extract:
                try:
                    archive_path.unlink()
                    result['deleted'] = True
                    logger.info(f"已删除: {archive_path.name}")
                except Exception as e:
                    logger.warning(f"删除失败 {archive_path.name}: {e}")
        else:
            result['message'] = message
            logger.error(f"解压失败 {archive_path.name}: {message}")

            # 清理空的解压目录
            try:
                if extract_dir.exists() and not any(extract_dir.iterdir()):
                    extract_dir.rmdir()
            except:
                pass

        return result

    def extract_all(
        self,
        archives: List[Path],
        progress_callback: Optional[callable] = None
    ) -> dict:
        """
        批量解压（串行）

        Args:
            archives: 压缩包列表
            progress_callback: 进度回调 (current, total, archive_name, result)

        Returns:
            统计结果
        """
        stats = {
            'total': len(archives),
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'deleted': 0,
            'details': []
        }

        for i, archive_path in enumerate(archives):
            result = self.extract(archive_path)
            stats['details'].append(result)

            if result['status'] == 'success':
                stats['success'] += 1
                if result['deleted']:
                    stats['deleted'] += 1
            elif result['status'] == 'skipped':
                stats['skipped'] += 1
            else:
                stats['failed'] += 1

            if progress_callback:
                progress_callback(i + 1, len(archives), archive_path.name, result)

        logger.info(
            f"批量解压完成: 成功={stats['success']}, "
            f"跳过={stats['skipped']}, "
            f"失败={stats['failed']}, "
            f"删除={stats['deleted']}"
        )

        return stats

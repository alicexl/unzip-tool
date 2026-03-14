# -*- coding: utf-8 -*-
"""
压缩包解压模块
支持 zip, rar, 7z 格式
"""

import zipfile
import logging
import re
import shutil
import subprocess
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

# 分卷压缩文件的首卷扩展名（只处理首卷，避免重复）
VOLUME_FIRST_EXTENSIONS = {'.001'}

# 所有分卷扩展名模式
VOLUME_PATTERN = re.compile(r'\.\d{3}$')


def find_7z_executable() -> Optional[str]:
    """查找 7z 可执行文件"""
    # 常见安装路径
    paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        "/usr/bin/7z",
        "/usr/local/bin/7z",
    ]

    for path in paths:
        if Path(path).exists():
            return path

    # 尝试从 PATH 查找
    result = shutil.which("7z")
    if result:
        return result

    return None


# 7z 可执行文件路径
SEVENZ_EXE = find_7z_executable()


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
        """检查文件是否是支持的压缩包（包括分卷）"""
        suffix = file_path.suffix.lower()

        # 普通压缩包
        if suffix in ARCHIVE_EXTENSIONS:
            return True

        # 分卷压缩包首卷 (.001)
        if suffix in VOLUME_FIRST_EXTENSIONS:
            # 检查是否是压缩包的分卷（如 .7z.001, .zip.001）
            name = file_path.name
            # 匹配 .7z.001, .zip.001, .rar.001 等格式
            for ext in ARCHIVE_EXTENSIONS:
                if name.endswith(f'{ext}.001'):
                    return True

        return False

    def is_volume_file(self, file_path: Path) -> bool:
        """检查是否是分卷压缩文件（非首卷）"""
        suffix = file_path.suffix.lower()
        # 匹配 .002, .003, ... 等分卷
        if VOLUME_PATTERN.match(suffix) and suffix != '.001':
            name = file_path.name
            for ext in ARCHIVE_EXTENSIONS:
                if re.search(rf'\{ext}\.\d{{3}}$', name):
                    return True
        return False

    def is_volume_archive(self, file_path: Path) -> bool:
        """检查是否是分卷压缩文件（首卷）"""
        return file_path.suffix.lower() == '.001'

    def get_all_volumes(self, first_volume: Path) -> List[Path]:
        """
        获取分卷压缩包的所有分卷文件

        Args:
            first_volume: 首卷文件路径 (.001)

        Returns:
            所有分卷文件列表
        """
        volumes = [first_volume]
        base = str(first_volume)[:-4]  # 去掉 .001

        # 查找后续分卷 .002, .003, ...
        for i in range(2, 1000):  # 最多支持 999 个分卷
            vol_path = Path(f"{base}.{i:03d}")
            if vol_path.exists():
                volumes.append(vol_path)
            else:
                break

        return volumes

    def _flatten_if_single_directory(self, extract_dir: Path, archive_path: Path) -> None:
        """
        如果解压结果是单一目录，将其内容提升到解压目录

        例如: extract_dir/photo/contents... -> extract_dir/contents...

        Args:
            extract_dir: 解压目录
            archive_path: 压缩包路径
        """
        try:
            if not extract_dir.exists() or not extract_dir.is_dir():
                return

            items = list(extract_dir.iterdir())

            # 只有一个项目且是目录
            if len(items) == 1 and items[0].is_dir():
                single_dir = items[0]
                parent = extract_dir.parent
                temp_dir = parent / f"_{extract_dir.name}_temp"

                # 将单目录重命名为临时名
                single_dir.rename(temp_dir)

                # 删除空的解压目录
                extract_dir.rmdir()

                # 将临时目录重命名为解压目录
                temp_dir.rename(extract_dir)

                logger.info(f"单目录提升: {single_dir.name} -> {extract_dir.name}")

        except Exception as e:
            logger.warning(f"单目录提升失败: {e}")

    def scan_archives(self, directory: Path) -> List[Path]:
        """
        递归扫描目录及子目录中的压缩包文件

        Args:
            directory: 目录路径

        Returns:
            压缩包文件列表
        """
        directory = directory.resolve()
        archives = []

        # 递归搜索所有子目录
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                # 跳过非首卷的分卷文件
                if self.is_volume_file(file_path):
                    continue
                if self.is_archive(file_path):
                    archives.append(file_path)
                    logger.debug(f"发现压缩包: {file_path.relative_to(directory)}")

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

    def extract_zip(self, archive_path: Path, extract_dir: Path, progress_callback=None) -> Tuple[bool, str]:
        """
        解压 ZIP 文件

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录
            progress_callback: 进度回调 (current, total, filename)

        Returns:
            (是否成功, 消息)
        """
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                # 检查是否是有效的 ZIP 文件
                bad_file = zf.testzip()
                if bad_file is not None:
                    return False, f"ZIP 文件损坏: {bad_file}"

                # 获取文件列表
                file_list = zf.namelist()
                total = len(file_list)
                pwd = self.password.encode() if self.password else None

                # 逐个解压并显示进度
                for i, filename in enumerate(file_list):
                    zf.extract(filename, extract_dir, pwd=pwd)
                    if progress_callback:
                        progress_callback(i + 1, total, filename)

            return True, "解压成功"

        except RuntimeError as e:
            if 'password' in str(e).lower() or 'encrypted' in str(e).lower():
                return False, "需要密码或密码错误"
            return False, f"解压失败: {e}"
        except zipfile.BadZipFile as e:
            return False, f"无效的 ZIP 文件: {e}"
        except Exception as e:
            return False, f"解压失败: {e}"

    def extract_rar(self, archive_path: Path, extract_dir: Path, progress_callback=None) -> Tuple[bool, str]:
        """
        解压 RAR 文件

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录
            progress_callback: 进度回调 (current, total, filename)

        Returns:
            (是否成功, 消息)
        """
        if not RAR_SUPPORTED:
            return False, "rarfile 库未安装，无法处理 RAR 文件"

        try:
            with rarfile.RarFile(archive_path, 'r') as rf:
                # 获取文件列表
                file_list = rf.namelist()
                total = len(file_list)

                # 逐个解压并显示进度
                for i, info in enumerate(rf.infolist()):
                    rf.extract(info, extract_dir, pwd=self.password)
                    if progress_callback:
                        progress_callback(i + 1, total, info.filename)

            return True, "解压成功"

        except rarfile.PasswordRequired:
            return False, "需要密码或密码错误"
        except rarfile.BadRarFile as e:
            return False, f"无效的 RAR 文件: {e}"
        except rarfile.NeedFirstVolume:
            return False, "需要 RAR 分卷的第一个文件"
        except Exception as e:
            return False, f"解压失败: {e}"

    def extract_7z(self, archive_path: Path, extract_dir: Path, progress_callback=None) -> Tuple[bool, str]:
        """
        解压 7z 文件（包括分卷）

        Args:
            archive_path: 压缩包路径
            extract_dir: 解压目标目录
            progress_callback: 进度回调 (current, total, filename)

        Returns:
            (是否成功, 消息)
        """
        is_volume = self.is_volume_archive(archive_path)

        # 分卷文件必须使用 7z.exe
        if is_volume:
            if not SEVENZ_EXE:
                return False, "分卷 7z 文件需要 7-Zip，请安装 7-Zip"
            return self._extract_7z_with_cli(archive_path, extract_dir, progress_callback)

        # 普通 7z 文件优先使用 py7zr
        if SEVENZ_SUPPORTED:
            return self._extract_7z_with_py7zr(archive_path, extract_dir, progress_callback)

        # 回退到 7z.exe
        if SEVENZ_EXE:
            return self._extract_7z_with_cli(archive_path, extract_dir, progress_callback)

        return False, "py7zr 库和 7-Zip 均不可用"

    def _extract_7z_with_py7zr(self, archive_path: Path, extract_dir: Path, progress_callback=None) -> Tuple[bool, str]:
        """使用 py7zr 库解压"""
        try:
            with py7zr.SevenZipFile(archive_path, 'r', password=self.password) as szf:
                file_list = szf.getnames()
                total = len(file_list)

                if progress_callback and total > 0:
                    progress_callback(0, total, "准备解压...")

                szf.extractall(extract_dir)

                if progress_callback and total > 0:
                    for i, filename in enumerate(file_list):
                        progress_callback(i + 1, total, filename)

            return True, "解压成功"

        except py7zr.exceptions.PasswordRequired:
            return False, "需要密码或密码错误"
        except py7zr.exceptions.Bad7zFile as e:
            return False, f"无效的 7z 文件: {e}"
        except Exception as e:
            if 'password' in str(e).lower():
                return False, "需要密码或密码错误"
            return False, f"解压失败: {e}"

    def _extract_7z_with_cli(self, archive_path: Path, extract_dir: Path, progress_callback=None) -> Tuple[bool, str]:
        """使用 7z.exe 命令行解压（支持分卷）"""
        try:
            cmd = [SEVENZ_EXE, 'x', str(archive_path), f'-o{extract_dir}', '-y']

            if self.password:
                cmd.append(f'-p{self.password}')

            if progress_callback:
                progress_callback(0, 1, "正在解压...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1小时超时
            )

            if result.returncode == 0:
                if progress_callback:
                    progress_callback(1, 1, "完成")
                return True, "解压成功"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                if 'Wrong password' in error_msg or '密码' in error_msg:
                    return False, "需要密码或密码错误"
                return False, f"解压失败: {error_msg[:100]}"

        except subprocess.TimeoutExpired:
            return False, "解压超时"
        except Exception as e:
            return False, f"解压失败: {e}"

    def extract(self, archive_path: Path, file_progress_callback=None) -> dict:
        """
        解压单个压缩包

        Args:
            archive_path: 压缩包路径
            file_progress_callback: 文件级进度回调 (current, total, filename)

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

        # 处理分卷文件 (.001, .002 等)
        if ext == '.001' or self.is_volume_archive(archive_path):
            # 从文件名推断实际格式 (如 xxx.7z.001 -> 7z)
            name = archive_path.name
            if '.7z.' in name:
                success, message = self.extract_7z(archive_path, extract_dir, file_progress_callback)
            elif '.zip.' in name:
                success, message = self.extract_zip(archive_path, extract_dir, file_progress_callback)
            elif '.rar.' in name:
                success, message = self.extract_rar(archive_path, extract_dir, file_progress_callback)
            else:
                result['message'] = f"未知的分卷格式: {name}"
                return result
        elif ext == '.zip':
            success, message = self.extract_zip(archive_path, extract_dir, file_progress_callback)
        elif ext == '.rar':
            success, message = self.extract_rar(archive_path, extract_dir, file_progress_callback)
        elif ext == '.7z':
            success, message = self.extract_7z(archive_path, extract_dir, file_progress_callback)
        else:
            result['message'] = f"不支持的格式: {ext}"
            return result

        if success:
            result['status'] = 'success'
            result['message'] = message
            logger.info(f"解压成功: {archive_path.name} -> {extract_dir.name}")

            # 智能处理：如果解压出单一目录，提升其内容
            self._flatten_if_single_directory(extract_dir, archive_path)

            # 删除压缩包
            if self.delete_after_extract:
                deleted_count = 0

                # 如果是分卷文件，删除所有分卷
                if self.is_volume_archive(archive_path):
                    all_volumes = self.get_all_volumes(archive_path)
                    for vol in all_volumes:
                        try:
                            vol.unlink()
                            deleted_count += 1
                            logger.info(f"已删除分卷: {vol.name}")
                        except Exception as e:
                            logger.warning(f"删除分卷失败 {vol.name}: {e}")
                else:
                    # 普通压缩包
                    try:
                        archive_path.unlink()
                        deleted_count = 1
                        logger.info(f"已删除: {archive_path.name}")
                    except Exception as e:
                        logger.warning(f"删除失败 {archive_path.name}: {e}")

                result['deleted'] = deleted_count > 0
                result['deleted_count'] = deleted_count
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
        progress_callback: Optional[callable] = None,
        file_progress_callback: Optional[callable] = None
    ) -> dict:
        """
        批量解压（串行），支持递归解压

        解压成功后会扫描解压目录，发现新压缩包则追加到任务列表

        Args:
            archives: 压缩包列表
            progress_callback: 压缩包级进度回调 (current, total, archive_name, result)
            file_progress_callback: 文件级进度回调 (archive_name, file_current, file_total, filename)

        Returns:
            统计结果
        """
        stats = {
            'total': len(archives),
            'initial': len(archives),
            'discovered': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'deleted': 0,
            'details': []
        }

        # 使用索引遍历，支持动态添加任务
        i = 0
        while i < len(archives):
            archive_path = archives[i]

            # 创建文件级进度回调包装器
            def file_callback(current, total, filename):
                if file_progress_callback:
                    file_progress_callback(archive_path.name, current, total, filename)

            result = self.extract(archive_path, file_progress_callback=file_callback)
            stats['details'].append(result)

            if result['status'] == 'success':
                stats['success'] += 1
                if result.get('deleted'):
                    stats['deleted'] += result.get('deleted_count', 1)

                # 扫描解压目录，发现新压缩包
                extract_dir = result.get('extract_dir')
                if extract_dir and extract_dir.exists():
                    new_archives = self.scan_archives(extract_dir)
                    if new_archives:
                        # 追加到任务列表末尾
                        archives.extend(new_archives)
                        stats['total'] = len(archives)
                        stats['discovered'] += len(new_archives)
                        logger.info(f"发现 {len(new_archives)} 个嵌套压缩包，已追加到任务列表")

            elif result['status'] == 'skipped':
                stats['skipped'] += 1
            else:
                stats['failed'] += 1

            if progress_callback:
                progress_callback(i + 1, len(archives), archive_path, result)

            i += 1

        logger.info(
            f"批量解压完成: 初始={stats['initial']}, "
            f"发现={stats['discovered']}, "
            f"成功={stats['success']}, "
            f"跳过={stats['skipped']}, "
            f"失败={stats['failed']}, "
            f"删除={stats['deleted']}"
        )

        return stats

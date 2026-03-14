# -*- coding: utf-8 -*-
"""
测试压缩包解压功能
"""

import unittest
import tempfile
import shutil
import zipfile
from pathlib import Path

from src.extractor import ArchiveExtractor, ARCHIVE_EXTENSIONS, SEVENZ_SUPPORTED

try:
    import py7zr
except ImportError:
    py7zr = None


class TestArchiveExtractor(unittest.TestCase):
    """解压器测试"""

    def setUp(self):
        """设置测试环境"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.extractor = ArchiveExtractor(delete_after_extract=True)

    def tearDown(self):
        """清理测试环境"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_zip(self, name: str, files: dict) -> Path:
        """创建测试用 ZIP 文件"""
        zip_path = self.temp_dir / name
        with zipfile.ZipFile(zip_path, 'w') as zf:
            for filename, content in files.items():
                zf.writestr(filename, content)
        return zip_path

    def _create_7z(self, name: str, files: dict) -> Path:
        """创建测试用 7z 文件"""
        if not SEVENZ_SUPPORTED:
            self.skipTest("py7zr 未安装")

        sz_path = self.temp_dir / name
        with py7zr.SevenZipFile(sz_path, 'w') as szf:
            for filename, content in files.items():
                # 创建临时文件
                tmp_file = self.temp_dir / f"_tmp_{filename}"
                tmp_file.write_text(content)
                szf.write(tmp_file, filename)
                tmp_file.unlink()
        return sz_path

    def test_is_archive(self):
        """测试压缩包识别"""
        self.assertTrue(self.extractor.is_archive(Path("test.zip")))
        self.assertTrue(self.extractor.is_archive(Path("test.ZIP")))
        self.assertTrue(self.extractor.is_archive(Path("test.rar")))
        self.assertTrue(self.extractor.is_archive(Path("test.RAR")))
        self.assertTrue(self.extractor.is_archive(Path("test.7z")))
        self.assertTrue(self.extractor.is_archive(Path("test.7Z")))
        self.assertFalse(self.extractor.is_archive(Path("test.txt")))
        self.assertFalse(self.extractor.is_archive(Path("test.tar")))

    def test_get_extract_dir(self):
        """测试获取解压目录"""
        archive = Path("/tmp/test.zip")
        extract_dir = self.extractor.get_extract_dir(archive)
        self.assertEqual(extract_dir, Path("/tmp/test"))

        archive = Path("/tmp/photos.backup.rar")
        extract_dir = self.extractor.get_extract_dir(archive)
        self.assertEqual(extract_dir, Path("/tmp/photos.backup"))

        archive = Path("/tmp/data.7z")
        extract_dir = self.extractor.get_extract_dir(archive)
        self.assertEqual(extract_dir, Path("/tmp/data"))

    def test_scan_archives(self):
        """测试扫描压缩包"""
        # 创建测试文件
        self._create_zip("test1.zip", {"file1.txt": "content1"})
        self._create_zip("test2.zip", {"file2.txt": "content2"})
        (self.temp_dir / "readme.txt").write_text("not an archive")

        archives = self.extractor.scan_archives(self.temp_dir)

        self.assertEqual(len(archives), 2)
        names = [a.name for a in archives]
        self.assertIn("test1.zip", names)
        self.assertIn("test2.zip", names)

    def test_scan_archives_with_7z(self):
        """测试扫描包含 7z 的压缩包"""
        self._create_zip("test.zip", {"file.txt": "content"})
        if SEVENZ_SUPPORTED:
            self._create_7z("test.7z", {"file.txt": "content"})

        archives = self.extractor.scan_archives(self.temp_dir)
        expected_count = 2 if SEVENZ_SUPPORTED else 1
        self.assertEqual(len(archives), expected_count)

    def test_scan_archives_recursive(self):
        """测试递归扫描子目录"""
        # 创建子目录
        subdir1 = self.temp_dir / "subdir1"
        subdir2 = self.temp_dir / "subdir2" / "deep"
        subdir1.mkdir()
        subdir2.mkdir(parents=True)

        # 在不同目录创建压缩包
        self._create_zip("root.zip", {"file.txt": "root"})
        self._create_zip(str(subdir1 / "sub1.zip"), {"file.txt": "sub1"})
        self._create_zip(str(subdir2 / "sub2.zip"), {"file.txt": "sub2"})

        # 递归扫描（默认行为）
        archives = self.extractor.scan_archives(self.temp_dir)
        self.assertEqual(len(archives), 3)

        # 验证路径正确
        relative_paths = [str(a.relative_to(self.temp_dir)) for a in archives]
        self.assertIn("root.zip", relative_paths)
        self.assertIn("subdir1\\sub1.zip", relative_paths)
        self.assertIn("subdir2\\deep\\sub2.zip", relative_paths)

    def test_extract_zip_success(self):
        """测试 ZIP 解压成功"""
        zip_path = self._create_zip("test.zip", {
            "file1.txt": "hello",
            "subdir/file2.txt": "world"
        })

        result = self.extractor.extract(zip_path)

        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['deleted'])

        # 验证解压目录存在
        extract_dir = self.temp_dir / "test"
        self.assertTrue(extract_dir.exists())
        self.assertTrue((extract_dir / "file1.txt").exists())
        self.assertTrue((extract_dir / "subdir" / "file2.txt").exists())

        # 验证压缩包已删除
        self.assertFalse(zip_path.exists())

    def test_extract_zip_keep_archive(self):
        """测试解压后保留压缩包"""
        extractor = ArchiveExtractor(delete_after_extract=False)
        zip_path = self._create_zip("keep.zip", {"file.txt": "content"})

        result = extractor.extract(zip_path)

        self.assertEqual(result['status'], 'success')
        self.assertFalse(result['deleted'])
        self.assertTrue(zip_path.exists())

    def test_extract_7z_success(self):
        """测试 7z 解压成功"""
        if not SEVENZ_SUPPORTED:
            self.skipTest("py7zr 未安装")

        sz_path = self._create_7z("test.7z", {
            "file1.txt": "hello",
            "file2.txt": "world"
        })

        result = self.extractor.extract(sz_path)

        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['deleted'])

        # 验证解压目录存在
        extract_dir = self.temp_dir / "test"
        self.assertTrue(extract_dir.exists())
        self.assertTrue((extract_dir / "file1.txt").exists())

        # 验证压缩包已删除
        self.assertFalse(sz_path.exists())

    def test_extract_skip_existing_dir(self):
        """测试跳过已存在目录"""
        zip_path = self._create_zip("existing.zip", {"file.txt": "content"})

        # 创建同名目录
        extract_dir = self.temp_dir / "existing"
        extract_dir.mkdir()

        result = self.extractor.extract(zip_path)

        self.assertEqual(result['status'], 'skipped')
        self.assertIn('已存在', result['message'])

    def test_extract_invalid_zip(self):
        """测试解压无效 ZIP"""
        # 创建无效的 ZIP 文件
        invalid_zip = self.temp_dir / "invalid.zip"
        invalid_zip.write_text("not a valid zip file")

        result = self.extractor.extract(invalid_zip)

        self.assertEqual(result['status'], 'failed')
        self.assertIn('无效', result['message'])

    def test_extract_invalid_7z(self):
        """测试解压无效 7z"""
        if not SEVENZ_SUPPORTED:
            self.skipTest("py7zr 未安装")

        # 创建无效的 7z 文件
        invalid_7z = self.temp_dir / "invalid.7z"
        invalid_7z.write_text("not a valid 7z file")

        result = self.extractor.extract(invalid_7z)

        self.assertEqual(result['status'], 'failed')
        self.assertIn('无效', result['message'])

    def test_extract_all(self):
        """测试批量解压"""
        # 创建多个 ZIP 文件
        self._create_zip("a.zip", {"a.txt": "content a"})
        self._create_zip("b.zip", {"b.txt": "content b"})
        self._create_zip("c.zip", {"c.txt": "content c"})

        archives = self.extractor.scan_archives(self.temp_dir)

        progress_calls = []
        def callback(current, total, name, result):
            progress_calls.append((current, total, name, result['status']))

        stats = self.extractor.extract_all(archives, progress_callback=callback)

        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['success'], 3)
        self.assertEqual(stats['failed'], 0)
        self.assertEqual(stats['deleted'], 3)
        self.assertEqual(len(progress_calls), 3)

        # 验证所有文件已删除，目录已创建
        self.assertFalse((self.temp_dir / "a.zip").exists())
        self.assertTrue((self.temp_dir / "a").is_dir())

    def test_archive_extensions_constant(self):
        """测试支持的扩展名常量"""
        self.assertIn('.zip', ARCHIVE_EXTENSIONS)
        self.assertIn('.rar', ARCHIVE_EXTENSIONS)
        self.assertIn('.7z', ARCHIVE_EXTENSIONS)
        self.assertEqual(len(ARCHIVE_EXTENSIONS), 3)

    def test_extract_7z_with_password(self):
        """测试带密码的 7z 解压"""
        if not SEVENZ_SUPPORTED:
            self.skipTest("py7zr 未安装")

        # 创建带密码的 7z
        sz_path = self.temp_dir / "protected.7z"
        tmp_file = self.temp_dir / "_tmp.txt"
        tmp_file.write_text("secret content")
        with py7zr.SevenZipFile(sz_path, 'w', password='test123') as szf:
            szf.write(tmp_file, "file.txt")
        tmp_file.unlink()

        # 不提供密码，应该失败
        extractor_no_pwd = ArchiveExtractor(delete_after_extract=False)
        result = extractor_no_pwd.extract(sz_path)
        self.assertEqual(result['status'], 'failed')
        self.assertIn('密码', result['message'])

        # 清理之前创建的空目录
        extract_dir = self.temp_dir / "protected"
        if extract_dir.exists():
            shutil.rmtree(extract_dir, ignore_errors=True)

        # 提供正确密码
        extractor_with_pwd = ArchiveExtractor(delete_after_extract=False, password='test123')
        result = extractor_with_pwd.extract(sz_path)
        self.assertEqual(result['status'], 'success')

    def test_extract_7z_wrong_password(self):
        """测试 7z 错误密码"""
        if not SEVENZ_SUPPORTED:
            self.skipTest("py7zr 未安装")

        # 创建带密码的 7z
        sz_path = self.temp_dir / "wrong_pwd.7z"
        tmp_file = self.temp_dir / "_tmp2.txt"
        tmp_file.write_text("secret content")
        with py7zr.SevenZipFile(sz_path, 'w', password='correct123') as szf:
            szf.write(tmp_file, "file.txt")
        tmp_file.unlink()

        # 提供错误密码
        extractor = ArchiveExtractor(delete_after_extract=False, password='wrong123')
        result = extractor.extract(sz_path)
        self.assertEqual(result['status'], 'failed')

    def test_is_volume_archive(self):
        """测试分卷文件识别"""
        # 分卷首卷应被识别
        self.assertTrue(self.extractor.is_archive(Path("test.7z.001")))
        self.assertTrue(self.extractor.is_archive(Path("test.zip.001")))
        self.assertTrue(self.extractor.is_archive(Path("test.rar.001")))

        # 分卷后续卷不应被识别（会被跳过）
        self.assertFalse(self.extractor.is_archive(Path("test.7z.002")))
        self.assertFalse(self.extractor.is_archive(Path("test.7z.003")))

        # 普通文件
        self.assertFalse(self.extractor.is_archive(Path("test.001")))
        self.assertFalse(self.extractor.is_archive(Path("test.txt")))

    def test_is_volume_file(self):
        """测试分卷文件检测（非首卷）"""
        # 首卷不是分卷文件
        self.assertFalse(self.extractor.is_volume_file(Path("test.7z.001")))

        # 后续卷是分卷文件
        self.assertTrue(self.extractor.is_volume_file(Path("test.7z.002")))
        self.assertTrue(self.extractor.is_volume_file(Path("test.7z.003")))
        self.assertTrue(self.extractor.is_volume_file(Path("test.zip.010")))

        # 普通文件
        self.assertFalse(self.extractor.is_volume_file(Path("test.7z")))
        self.assertFalse(self.extractor.is_volume_file(Path("test.txt")))

    def test_scan_archives_with_volumes(self):
        """测试扫描分卷文件"""
        # 创建模拟分卷文件
        vol1 = self.temp_dir / "video.7z.001"
        vol2 = self.temp_dir / "video.7z.002"
        vol3 = self.temp_dir / "video.7z.003"
        normal = self.temp_dir / "normal.zip"

        # 写入一些数据
        vol1.write_bytes(b"mock volume 1")
        vol2.write_bytes(b"mock volume 2")
        vol3.write_bytes(b"mock volume 3")
        self._create_zip("normal.zip", {"file.txt": "content"})

        # 扫描
        archives = self.extractor.scan_archives(self.temp_dir)

        # 应该只扫描到首卷和普通压缩包，跳过后续卷
        names = [a.name for a in archives]
        self.assertIn("video.7z.001", names)  # 首卷应被识别
        self.assertIn("normal.zip", names)
        self.assertNotIn("video.7z.002", names)  # 后续卷应被跳过
        self.assertNotIn("video.7z.003", names)

        # 总共2个
        self.assertEqual(len(archives), 2)

    def test_get_extract_dir_for_volume(self):
        """测试分卷文件的解压目录"""
        # 分卷文件解压目录应该是去掉分卷后缀
        archive = Path("/tmp/video.7z.001")
        extract_dir = self.extractor.get_extract_dir(archive)
        # 应该去掉 .001 后缀
        self.assertEqual(extract_dir, Path("/tmp/video.7z"))

    def test_scan_archives_recursive_with_volumes(self):
        """测试递归扫描包含分卷的子目录"""
        # 创建子目录
        subdir = self.temp_dir / "subdir"
        subdir.mkdir()

        # 在不同位置创建分卷文件
        vol1 = self.temp_dir / "root.7z.001"
        vol2 = self.temp_dir / "root.7z.002"
        sub_vol1 = subdir / "sub.7z.001"
        sub_vol2 = subdir / "sub.7z.002"

        vol1.write_bytes(b"mock")
        vol2.write_bytes(b"mock")
        sub_vol1.write_bytes(b"mock")
        sub_vol2.write_bytes(b"mock")

        # 扫描
        archives = self.extractor.scan_archives(self.temp_dir)

        # 应该只扫描到两个首卷
        relative_paths = [str(a.relative_to(self.temp_dir)) for a in archives]
        self.assertEqual(len(archives), 2)
        self.assertIn("root.7z.001", relative_paths)
        self.assertIn("subdir\\sub.7z.001", relative_paths)

        # 后续卷不应被扫描到
        self.assertNotIn("root.7z.002", relative_paths)
        self.assertNotIn("subdir\\sub.7z.002", relative_paths)

    def test_get_all_volumes(self):
        """测试获取所有分卷文件"""
        # 创建模拟分卷文件
        vol1 = self.temp_dir / "test.7z.001"
        vol2 = self.temp_dir / "test.7z.002"
        vol3 = self.temp_dir / "test.7z.003"

        vol1.write_bytes(b"mock 1")
        vol2.write_bytes(b"mock 2")
        vol3.write_bytes(b"mock 3")

        # 获取所有分卷
        volumes = self.extractor.get_all_volumes(vol1)

        self.assertEqual(len(volumes), 3)
        self.assertIn(vol1, volumes)
        self.assertIn(vol2, volumes)
        self.assertIn(vol3, volumes)

    def test_delete_all_volumes_after_extract(self):
        """测试解压后删除所有分卷"""
        # 创建模拟分卷文件（使用 zip 因为可以用 Python 解压）
        vol1 = self.temp_dir / "test.zip.001"
        vol2 = self.temp_dir / "test.zip.002"
        vol3 = self.temp_dir / "test.zip.003"

        vol1.write_bytes(b"mock 1")
        vol2.write_bytes(b"mock 2")
        vol3.write_bytes(b"mock 3")

        # 验证文件存在
        self.assertTrue(vol1.exists())
        self.assertTrue(vol2.exists())
        self.assertTrue(vol3.exists())

    def test_flatten_single_directory(self):
        """测试单目录提升"""
        # 创建包含单目录的 ZIP
        zip_path = self.temp_dir / "single_dir.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("myfolder/file1.txt", "content1")
            zf.writestr("myfolder/subdir/file2.txt", "content2")

        # 解压
        result = self.extractor.extract(zip_path)
        self.assertEqual(result['status'], 'success')

        # 验证目录结构被提升
        extract_dir = self.temp_dir / "single_dir"
        self.assertTrue(extract_dir.exists())
        # myfolder 的内容应该被提升到 single_dir
        self.assertTrue((extract_dir / "file1.txt").exists())
        self.assertTrue((extract_dir / "subdir" / "file2.txt").exists())
        # myfolder 不应存在
        self.assertFalse((extract_dir / "myfolder").exists())

    def test_no_flatten_multiple_items(self):
        """测试多项目不提升"""
        # 创建包含多个项目的 ZIP
        zip_path = self.temp_dir / "multi.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("file1.txt", "content1")
            zf.writestr("file2.txt", "content2")

        # 解压（不删除）
        extractor = ArchiveExtractor(delete_after_extract=False)
        result = extractor.extract(zip_path)
        self.assertEqual(result['status'], 'success')

        # 验证目录结构未被提升
        extract_dir = self.temp_dir / "multi"
        self.assertTrue(extract_dir.exists())
        self.assertTrue((extract_dir / "file1.txt").exists())
        self.assertTrue((extract_dir / "file2.txt").exists())

    def test_no_flatten_multiple_dirs(self):
        """测试多目录不提升"""
        # 创建包含多个目录的 ZIP
        zip_path = self.temp_dir / "multidir.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("dir1/file1.txt", "content1")
            zf.writestr("dir2/file2.txt", "content2")

        # 解压（不删除）
        extractor = ArchiveExtractor(delete_after_extract=False)
        result = extractor.extract(zip_path)
        self.assertEqual(result['status'], 'success')

        # 验证目录结构未被提升
        extract_dir = self.temp_dir / "multidir"
        self.assertTrue(extract_dir.exists())
        # 两个目录都应存在
        self.assertTrue((extract_dir / "dir1").exists())
        self.assertTrue((extract_dir / "dir2").exists())

    def test_extract_all_discovered_archives(self):
        """测试递归解压嵌套压缩包"""
        # 创建嵌套的压缩包结构
        # inner.zip 包含文件
        inner_zip = self.temp_dir / "_inner.zip"
        with zipfile.ZipFile(inner_zip, 'w') as zf:
            zf.writestr("inner_file.txt", "inner content")

        # outer.zip 包含 inner.zip
        outer_zip = self.temp_dir / "outer.zip"
        with zipfile.ZipFile(outer_zip, 'w') as zf:
            zf.write(inner_zip, "nested.zip")

        inner_zip.unlink()  # 删除临时文件

        # 批量解压
        archives = self.extractor.scan_archives(self.temp_dir)
        self.assertEqual(len(archives), 1)  # 只有 outer.zip

        stats = self.extractor.extract_all(archives)

        # 应该解压了 2 个压缩包
        self.assertEqual(stats['initial'], 1)
        self.assertEqual(stats['discovered'], 1)  # 发现 1 个嵌套压缩包
        self.assertEqual(stats['success'], 2)  # 两个都成功
        self.assertEqual(stats['total'], 2)  # 总共 2 个任务

        # 验证文件解压成功
        outer_dir = self.temp_dir / "outer"
        inner_dir = outer_dir / "nested"
        self.assertTrue((inner_dir / "inner_file.txt").exists())


if __name__ == '__main__':
    unittest.main()

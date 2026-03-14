# -*- coding: utf-8 -*-
"""
测试压缩包解压功能
"""

import unittest
import tempfile
import shutil
import zipfile
from pathlib import Path

from src.extractor import ArchiveExtractor, ARCHIVE_EXTENSIONS


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

    def test_is_archive(self):
        """测试压缩包识别"""
        self.assertTrue(self.extractor.is_archive(Path("test.zip")))
        self.assertTrue(self.extractor.is_archive(Path("test.ZIP")))
        self.assertTrue(self.extractor.is_archive(Path("test.rar")))
        self.assertTrue(self.extractor.is_archive(Path("test.RAR")))
        self.assertFalse(self.extractor.is_archive(Path("test.txt")))
        self.assertFalse(self.extractor.is_archive(Path("test.7z")))

    def test_get_extract_dir(self):
        """测试获取解压目录"""
        archive = Path("/tmp/test.zip")
        extract_dir = self.extractor.get_extract_dir(archive)
        self.assertEqual(extract_dir, Path("/tmp/test"))

        archive = Path("/tmp/photos.backup.rar")
        extract_dir = self.extractor.get_extract_dir(archive)
        self.assertEqual(extract_dir, Path("/tmp/photos.backup"))

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
        self.assertEqual(len(ARCHIVE_EXTENSIONS), 2)


if __name__ == '__main__':
    unittest.main()

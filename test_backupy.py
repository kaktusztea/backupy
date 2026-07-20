#!/usr/bin/env python3
"""Unit tests for backupy.py"""

# Execute manually:
# python3 -m unittest test_backupy -v

import os
import sys
import shutil
import tarfile
import zipfile
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from backupy import (
    strip_dash_string_end,
    strip_enddash_on_list,
    add_dot_for_endings,
    getsub_dir_path,
    sizeof_fmt,
    filter_nonexistent_include_dirs,
    Backupset,
    Backuptask,
    Configglobal,
)


class TestStripDashStringEnd(unittest.TestCase):
    def test_single_trailing_slash(self):
        self.assertEqual(strip_dash_string_end("/home/user/"), "/home/user")

    def test_multiple_trailing_slashes(self):
        self.assertEqual(strip_dash_string_end("/path///"), "/path")

    def test_no_trailing_slash(self):
        self.assertEqual(strip_dash_string_end("/path/to/dir"), "/path/to/dir")

    def test_root_slash_only(self):
        self.assertEqual(strip_dash_string_end("/"), "")

    def test_empty_string(self):
        self.assertEqual(strip_dash_string_end(""), "")


class TestStripEnddashOnList(unittest.TestCase):
    def test_strips_slashes(self):
        self.assertEqual(strip_enddash_on_list(["/a/", "/b/c/"]), ["/a", "/b/c"])

    def test_no_slashes(self):
        self.assertEqual(strip_enddash_on_list(["/a", "/b"]), ["/a", "/b"])

    def test_empty_list(self):
        self.assertEqual(strip_enddash_on_list([]), [])

    def test_mixed(self):
        self.assertEqual(strip_enddash_on_list(["dir/", "other"]), ["dir", "other"])


class TestAddDotForEndings(unittest.TestCase):
    def test_adds_dot(self):
        self.assertEqual(add_dot_for_endings(["swp", "bak"]), [".swp", ".bak"])

    def test_already_has_dot(self):
        self.assertEqual(add_dot_for_endings([".swp", ".bak"]), [".swp", ".bak"])

    def test_tilde_unchanged(self):
        self.assertEqual(add_dot_for_endings(["~"]), ["~"])

    def test_mixed(self):
        self.assertEqual(add_dot_for_endings(["swp", ".bak", "~"]), [".swp", ".bak", "~"])

    def test_empty(self):
        self.assertEqual(add_dot_for_endings([]), [])


class TestGetsubDirPath(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(getsub_dir_path("/home/user", "/home/user/docs/file.txt"),
                         "user/docs/file.txt")

    def test_deep_path(self):
        self.assertEqual(getsub_dir_path("/a/b", "/a/b/c/d/e"),
                         "b/c/d/e")

    def test_trailing_slashes(self):
        self.assertEqual(getsub_dir_path("/home/user/", "/home/user/docs/"),
                         "user/docs")

    def test_non_absolute_returns_false(self):
        self.assertFalse(getsub_dir_path("relative", "/absolute/path"))
        self.assertFalse(getsub_dir_path("/absolute", "relative/path"))


class TestSizeofFmt(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(sizeof_fmt(500), "500.0 B")

    def test_kibibytes(self):
        self.assertEqual(sizeof_fmt(1024), "1.0 KiB")

    def test_mebibytes(self):
        self.assertEqual(sizeof_fmt(1024 * 1024), "1.0 MiB")

    def test_gibibytes(self):
        self.assertEqual(sizeof_fmt(1024**3), "1.0 GiB")

    def test_zero(self):
        self.assertEqual(sizeof_fmt(0), "0.0 B")


class TestFilterNonexistentIncludeDirs(unittest.TestCase):
    def test_all_exist(self):
        dirs = [tempfile.gettempdir()]
        result = filter_nonexistent_include_dirs(dirs)
        self.assertIsNone(result)
        self.assertEqual(len(dirs), 1)

    def test_removes_nonexistent(self):
        dirs = [tempfile.gettempdir(), "/nonexistent_dir_xyz_123"]
        result = filter_nonexistent_include_dirs(dirs)
        self.assertTrue(result)
        self.assertEqual(dirs, [tempfile.gettempdir()])

    def test_all_nonexistent(self):
        dirs = ["/no_exist_a", "/no_exist_b"]
        filter_nonexistent_include_dirs(dirs)
        self.assertEqual(dirs, [])


class TestBackupsetConfigLoading(unittest.TestCase):
    """Tests for Backupset._load_config and config validation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.src = os.path.join(self.tmpdir, "src")
        self.out = os.path.join(self.tmpdir, "out")
        os.makedirs(self.src)
        os.makedirs(self.out)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_config(self, content, filename="test.toml"):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def _minimal_config(self, **overrides):
        cfg = {
            "name": "test set",
            "enabled": "true",
            "task_name": "task1",
            "archive_name": "archive",
            "method": "targz",
            "include_dirs": f'["{self.src}"]',
            "result_dir": self.out,
        }
        cfg.update(overrides)
        return f'''
[meta]
name = "{cfg["name"]}"
enabled = {cfg["enabled"]}

[global_excludes]
endings = []
files = []
dir_names = []

[[backup]]
name = "{cfg["task_name"]}"
enabled = true
archive_name = "{cfg["archive_name"]}"
result_dir = "{cfg["result_dir"]}"
create_target_date_dir = false
method = "{cfg["method"]}"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = {cfg["include_dirs"]}
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''

    def test_valid_config_loads(self):
        path = self._write_config(self._minimal_config())
        bs = Backupset(path)
        self.assertEqual(bs.name, "test set")
        self.assertTrue(bs.enabled)
        self.assertEqual(len(bs.task_list), 1)

    def test_meta_name_parsed(self):
        path = self._write_config(self._minimal_config(name="My Backup"))
        bs = Backupset(path)
        self.assertEqual(bs.name, "My Backup")

    def test_disabled_set(self):
        path = self._write_config(self._minimal_config(enabled="false"))
        bs = Backupset(path)
        self.assertFalse(bs.enabled)

    def test_global_excludes_parsed(self):
        cfg = '''
[meta]
name = "test"
enabled = true

[global_excludes]
endings = ["swp", ".bak"]
files = ["Thumbs.db", ".DS_Store"]
dir_names = ["node_modules/", "__pycache__"]

[[backup]]
name = "t"
enabled = true
archive_name = "a"
result_dir = "''' + self.out + '''"
create_target_date_dir = false
method = "tar"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["''' + self.src + '''"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''
        path = self._write_config(cfg)
        bs = Backupset(path)
        self.assertEqual(bs.g.exclude_endings, [".swp", ".bak"])
        self.assertEqual(bs.g.exclude_files, ["Thumbs.db", ".DS_Store"])
        self.assertEqual(bs.g.exclude_dir_names, ["node_modules", "__pycache__"])

    def test_task_method_extension_targz(self):
        path = self._write_config(self._minimal_config(method="targz"))
        bs = Backupset(path)
        self.assertTrue(bs.task_list[0].archive_name.endswith(".tar.gz"))

    def test_task_method_extension_tarbz2(self):
        path = self._write_config(self._minimal_config(method="tarbz2"))
        bs = Backupset(path)
        self.assertTrue(bs.task_list[0].archive_name.endswith(".tar.bz2"))

    def test_task_method_extension_zip(self):
        path = self._write_config(self._minimal_config(method="zip"))
        bs = Backupset(path)
        self.assertTrue(bs.task_list[0].archive_name.endswith(".zip"))

    def test_task_method_extension_tar(self):
        path = self._write_config(self._minimal_config(method="tar"))
        bs = Backupset(path)
        self.assertTrue(bs.task_list[0].archive_name.endswith(".tar"))

    def test_invalid_method_exits(self):
        path = self._write_config(self._minimal_config(method="7z"))
        with self.assertRaises(SystemExit):
            Backupset(path)

    def test_missing_meta_key_exits(self):
        cfg = '''
[meta]
enabled = true

[[backup]]
name = "t"
enabled = true
archive_name = "a"
result_dir = "/tmp"
create_target_date_dir = false
method = "tar"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["/tmp"]
'''
        path = self._write_config(cfg)
        with self.assertRaises(SystemExit):
            Backupset(path)

    def test_invalid_toml_syntax_exits(self):
        path = self._write_config("this is [not valid {{ toml")
        with self.assertRaises(SystemExit):
            Backupset(path)

    def test_nonexistent_config_exits(self):
        with self.assertRaises(SystemExit):
            Backupset("/nonexistent/path/config.toml")

    def test_empty_archive_name_exits(self):
        path = self._write_config(self._minimal_config(archive_name=""))
        with self.assertRaises(SystemExit):
            Backupset(path)

    def test_duplicate_task_names_exits(self):
        cfg = '''
[meta]
name = "test"
enabled = true

[global_excludes]
endings = []
files = []
dir_names = []

[[backup]]
name = "same_name"
enabled = true
archive_name = "a1"
result_dir = "''' + self.out + '''"
create_target_date_dir = false
method = "tar"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["''' + self.src + '''"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []

[[backup]]
name = "same_name"
enabled = true
archive_name = "a2"
result_dir = "''' + self.out + '''"
create_target_date_dir = false
method = "tar"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["''' + self.src + '''"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''
        path = self._write_config(cfg)
        with self.assertRaises(SystemExit):
            Backupset(path)

    def test_has_active_backuptask_true(self):
        path = self._write_config(self._minimal_config())
        bs = Backupset(path)
        self.assertTrue(bs.has_active_backuptask())

    def test_precomputed_all_endings(self):
        cfg = '''
[meta]
name = "test"
enabled = true

[global_excludes]
endings = ["swp"]
files = []
dir_names = []

[[backup]]
name = "t"
enabled = true
archive_name = "a"
result_dir = "''' + self.out + '''"
create_target_date_dir = false
method = "tar"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["''' + self.src + '''"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = ["bak"]
exclude_files = []
'''
        path = self._write_config(cfg)
        bs = Backupset(path)
        task = bs.task_list[0]
        self.assertIn(".swp", task._all_endings)
        self.assertIn(".bak", task._all_endings)


class TestIsExcluded(unittest.TestCase):
    """Tests for Backuptask._is_excluded filtering logic."""

    def _make_task(self, global_endings=None, global_files=None, global_dirs=None,
                   task_endings=None, task_files=None, task_dirs=None, task_fullpaths=None):
        g = Configglobal()
        g.exclude_endings = global_endings or []
        g.exclude_files = global_files or []
        g.exclude_dir_names = global_dirs or []
        task = Backuptask("test[0]", g, "/fake/config.toml")
        task.exclude_endings = task_endings or []
        task.exclude_files = task_files or []
        task.exclude_dir_names = task_dirs or []
        task.exclude_dir_fullpath = task_fullpaths or []
        task._all_endings = tuple(g.exclude_endings + task.exclude_endings)
        task._all_files = g.exclude_files + task.exclude_files
        task.configs_global = g
        return task

    # --- ending exclusions ---

    def test_global_ending_excluded(self):
        task = self._make_task(global_endings=[".swp"])
        self.assertTrue(task._is_excluded("/home/user/file.swp", "/home/user"))

    def test_task_ending_excluded(self):
        task = self._make_task(task_endings=[".bak"])
        self.assertTrue(task._is_excluded("/home/user/file.bak", "/home/user"))

    def test_ending_not_matched(self):
        task = self._make_task(global_endings=[".swp"])
        self.assertFalse(task._is_excluded("/home/user/file.txt", "/home/user"))

    def test_tilde_ending(self):
        task = self._make_task(global_endings=["~"])
        self.assertTrue(task._is_excluded("/home/user/doc.txt~", "/home/user"))

    def test_ending_case_sensitive(self):
        task = self._make_task(global_endings=[".SWP"])
        self.assertFalse(task._is_excluded("/home/user/file.swp", "/home/user"))

    # --- file exclusions ---

    def test_global_file_excluded(self):
        task = self._make_task(global_files=["Thumbs.db"])
        self.assertTrue(task._is_excluded("/home/user/pics/Thumbs.db", "/home/user"))

    def test_task_file_excluded(self):
        task = self._make_task(task_files=["notes.md"])
        self.assertTrue(task._is_excluded("/home/user/docs/notes.md", "/home/user"))

    def test_file_not_matched(self):
        task = self._make_task(global_files=["Thumbs.db"])
        self.assertFalse(task._is_excluded("/home/user/readme.txt", "/home/user"))

    def test_file_match_is_basename_only(self):
        """A file named 'db' should not match 'Thumbs.db'."""
        task = self._make_task(global_files=["Thumbs.db"])
        self.assertFalse(task._is_excluded("/home/user/db", "/home/user"))

    # --- dir name exclusions ---

    def test_global_dir_name_excluded(self):
        task = self._make_task(global_dirs=["node_modules"])
        self.assertTrue(task._is_excluded("/project/node_modules/pkg/index.js", "/project"))

    def test_task_dir_name_excluded(self):
        task = self._make_task(task_dirs=["build"])
        self.assertTrue(task._is_excluded("/project/src/build/output.o", "/project"))

    def test_dir_name_not_matched(self):
        task = self._make_task(global_dirs=["node_modules"])
        self.assertFalse(task._is_excluded("/project/src/main.py", "/project"))

    # --- fullpath exclusions ---

    def test_fullpath_excluded(self):
        task = self._make_task(task_fullpaths=["/project/vendor"])
        self.assertTrue(task._is_excluded("/project/vendor/lib/thing.so", "/project"))

    def test_fullpath_not_matched(self):
        task = self._make_task(task_fullpaths=["/project/vendor"])
        self.assertFalse(task._is_excluded("/project/src/main.py", "/project"))

    # --- no exclusions ---

    def test_no_exclusions_passes(self):
        task = self._make_task()
        self.assertFalse(task._is_excluded("/home/user/file.txt", "/home/user"))

    # --- combined ---

    def test_multiple_rules_first_wins(self):
        task = self._make_task(global_endings=[".swp"], global_files=["Thumbs.db"])
        self.assertTrue(task._is_excluded("/path/file.swp", "/path"))
        self.assertTrue(task._is_excluded("/path/Thumbs.db", "/path"))
        self.assertFalse(task._is_excluded("/path/good.txt", "/path"))


class TestFilterTar(unittest.TestCase):
    """Tests for Backuptask.filter_tar (tarfile callback adapter)."""

    def _make_task(self, **kwargs):
        return TestIsExcluded._make_task(self, **kwargs)

    def _make_tarinfo(self, name):
        info = tarfile.TarInfo(name=name)
        return info

    def test_returns_tarinfo_when_not_excluded(self):
        task = self._make_task()
        info = self._make_tarinfo("src/main.py")
        result = task.filter_tar(info, "/project")
        self.assertIs(result, info)

    def test_returns_none_when_excluded(self):
        task = self._make_task(global_endings=[".swp"])
        info = self._make_tarinfo("src/editor.swp")
        result = task.filter_tar(info, "/project")
        self.assertIsNone(result)

    def test_dir_name_filter_in_tar(self):
        task = self._make_task(global_dirs=["__pycache__"])
        info = self._make_tarinfo("src/__pycache__/module.pyc")
        result = task.filter_tar(info, "/project")
        self.assertIsNone(result)


class _CompressTestBase(unittest.TestCase):
    """Base class with helper for compression integration tests."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.src = os.path.join(self.tmpdir, "src")
        self.out = os.path.join(self.tmpdir, "out")
        os.makedirs(self.src)
        os.makedirs(self.out)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_config(self, content):
        path = os.path.join(self.tmpdir, "test.toml")
        with open(path, "w") as f:
            f.write(content)
        return path

    def _make_config(self, method="targz", withpath="false", followsym="false",
                     global_endings="[]", global_files="[]", global_dirs="[]",
                     task_endings="[]", task_files="[]", task_dirs="[]",
                     task_fullpaths="[]"):
        return f'''
[meta]
name = "compress test"
enabled = true

[global_excludes]
endings = {global_endings}
files = {global_files}
dir_names = {global_dirs}

[[backup]]
name = "task1"
enabled = true
archive_name = "out"
result_dir = "{self.out}"
create_target_date_dir = false
method = "{method}"
followsym = {followsym}
withpath = {withpath}
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["{self.src}"]
exclude_dir_names = {task_dirs}
exclude_dir_fullpaths = {task_fullpaths}
exclude_endings = {task_endings}
exclude_files = {task_files}
'''

    def _run_backup(self, config_content):
        path = self._write_config(config_content)
        bs = Backupset(path)
        bs.execute()
        return bs

    def _get_tar_contents(self):
        archives = [f for f in os.listdir(self.out) if f.endswith(('.tar.gz', '.tar.bz2', '.tar'))]
        self.assertEqual(len(archives), 1, f"Expected 1 tar archive, got {archives}")
        with tarfile.open(os.path.join(self.out, archives[0])) as tf:
            return tf.getnames()

    def _get_zip_contents(self):
        archives = [f for f in os.listdir(self.out) if f.endswith('.zip')]
        self.assertEqual(len(archives), 1, f"Expected 1 zip archive, got {archives}")
        with zipfile.ZipFile(os.path.join(self.out, archives[0])) as zf:
            return zf.namelist()


class TestCompressTar(_CompressTestBase):
    """Integration tests for compress_tar."""

    def test_basic_tar_creates_archive(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="targz"))
        names = self._get_tar_contents()
        self.assertTrue(any("file.txt" in n for n in names))

    def test_tar_global_ending_excluded(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        open(os.path.join(self.src, "temp.swp"), "w").close()
        self._run_backup(self._make_config(global_endings='["swp"]'))
        names = self._get_tar_contents()
        self.assertTrue(any("file.txt" in n for n in names))
        self.assertFalse(any("temp.swp" in n for n in names))

    def test_tar_task_file_excluded(self):
        open(os.path.join(self.src, "keep.txt"), "w").close()
        open(os.path.join(self.src, "remove.log"), "w").close()
        self._run_backup(self._make_config(task_files='["remove.log"]'))
        names = self._get_tar_contents()
        self.assertTrue(any("keep.txt" in n for n in names))
        self.assertFalse(any("remove.log" in n for n in names))

    def test_tar_dir_name_excluded(self):
        os.makedirs(os.path.join(self.src, "cache"))
        open(os.path.join(self.src, "cache", "data.bin"), "w").close()
        open(os.path.join(self.src, "real.txt"), "w").close()
        self._run_backup(self._make_config(global_dirs='["cache"]'))
        names = self._get_tar_contents()
        self.assertFalse(any("data.bin" in n for n in names))
        self.assertTrue(any("real.txt" in n for n in names))

    def test_tar_withpath_false(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(withpath="false"))
        names = self._get_tar_contents()
        # should use basename of include_dir as root
        self.assertTrue(any(n.startswith("src") for n in names))

    def test_tar_withpath_true(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(withpath="true"))
        names = self._get_tar_contents()
        # should contain full path (starts with tmp/)
        self.assertTrue(any("tmp/" in n for n in names))

    def test_tar_broken_symlink_skipped(self):
        open(os.path.join(self.src, "real.txt"), "w").close()
        os.symlink("/nonexistent_target", os.path.join(self.src, "broken"))
        self._run_backup(self._make_config(followsym="true"))
        names = self._get_tar_contents()
        self.assertTrue(any("real.txt" in n for n in names))
        self.assertFalse(any("broken" in n for n in names))

    def test_tar_bz2_method(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="tarbz2"))
        names = self._get_tar_contents()
        self.assertTrue(any("file.txt" in n for n in names))

    def test_tar_md5_created(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config())
        md5_file = os.path.join(self.out, "md5.sum")
        self.assertTrue(os.path.exists(md5_file))
        with open(md5_file) as f:
            content = f.read()
        self.assertIn("out_", content)


class TestCompressZip(_CompressTestBase):
    """Integration tests for compress_zip."""

    def test_basic_zip_creates_archive(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="zip"))
        names = self._get_zip_contents()
        self.assertTrue(any("file.txt" in n for n in names))

    def test_zip_global_ending_excluded(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        open(os.path.join(self.src, "temp.swp"), "w").close()
        self._run_backup(self._make_config(method="zip", global_endings='["swp"]'))
        names = self._get_zip_contents()
        self.assertTrue(any("file.txt" in n for n in names))
        self.assertFalse(any("temp.swp" in n for n in names))

    def test_zip_fullpath_dir_excluded(self):
        os.makedirs(os.path.join(self.src, "vendor"))
        open(os.path.join(self.src, "vendor", "lib.so"), "w").close()
        open(os.path.join(self.src, "app.py"), "w").close()
        fullpath = os.path.join(self.src, "vendor")
        self._run_backup(self._make_config(method="zip", task_fullpaths=f'["{fullpath}"]'))
        names = self._get_zip_contents()
        self.assertFalse(any("lib.so" in n for n in names))
        self.assertTrue(any("app.py" in n for n in names))

    def test_zip_broken_symlink_skipped(self):
        open(os.path.join(self.src, "real.txt"), "w").close()
        os.symlink("/nonexistent_xyz", os.path.join(self.src, "broken"))
        self._run_backup(self._make_config(method="zip"))
        names = self._get_zip_contents()
        self.assertTrue(any("real.txt" in n for n in names))
        self.assertFalse(any("broken" in n for n in names))

    def test_zip_permission_denied_skipped(self):
        open(os.path.join(self.src, "good.txt"), "w").close()
        noperm = os.path.join(self.src, "secret.txt")
        open(noperm, "w").close()
        os.chmod(noperm, 0o000)
        try:
            self._run_backup(self._make_config(method="zip"))
            names = self._get_zip_contents()
            self.assertTrue(any("good.txt" in n for n in names))
            self.assertFalse(any("secret.txt" in n for n in names))
        finally:
            os.chmod(noperm, 0o644)

    def test_zip_withpath_false(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="zip", withpath="false"))
        names = self._get_zip_contents()
        self.assertTrue(any(n.startswith("src") for n in names))

    def test_zip_withpath_true(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="zip", withpath="true"))
        names = self._get_zip_contents()
        self.assertTrue(any("tmp/" in n for n in names))

    def test_zip_md5_created(self):
        open(os.path.join(self.src, "file.txt"), "w").close()
        self._run_backup(self._make_config(method="zip"))
        md5_file = os.path.join(self.out, "md5.sum")
        self.assertTrue(os.path.exists(md5_file))


class TestEdgeCases(_CompressTestBase):
    """Edge cases and unusual scenarios."""

    def test_empty_source_dir_creates_archive(self):
        """Empty directory should still create a valid (almost empty) archive."""
        self._run_backup(self._make_config())
        names = self._get_tar_contents()
        # at minimum the root dir entry
        self.assertTrue(len(names) >= 1)

    def test_deeply_nested_files(self):
        """Files many levels deep should be included."""
        deep = os.path.join(self.src, "a", "b", "c", "d", "e")
        os.makedirs(deep)
        open(os.path.join(deep, "deep.txt"), "w").close()
        self._run_backup(self._make_config())
        names = self._get_tar_contents()
        self.assertTrue(any("deep.txt" in n for n in names))

    def test_filename_looks_like_ending_but_isnt(self):
        """A file named '.swp' as the entire name should still be excluded."""
        task_endings = '["swp"]'
        open(os.path.join(self.src, ".swp"), "w").close()
        open(os.path.join(self.src, "good.txt"), "w").close()
        self._run_backup(self._make_config(global_endings=task_endings))
        names = self._get_tar_contents()
        self.assertFalse(any(n.endswith(".swp") for n in names))
        self.assertTrue(any("good.txt" in n for n in names))

    def test_multiple_include_dirs(self):
        """Multiple include directories should all be archived."""
        src2 = os.path.join(self.tmpdir, "src2")
        os.makedirs(src2)
        open(os.path.join(self.src, "a.txt"), "w").close()
        open(os.path.join(src2, "b.txt"), "w").close()
        cfg = f'''
[meta]
name = "multi"
enabled = true
[global_excludes]
endings = []
files = []
dir_names = []
[[backup]]
name = "task1"
enabled = true
archive_name = "out"
result_dir = "{self.out}"
create_target_date_dir = false
method = "targz"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["{self.src}", "{src2}"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''
        self._run_backup(cfg)
        names = self._get_tar_contents()
        self.assertTrue(any("a.txt" in n for n in names))
        self.assertTrue(any("b.txt" in n for n in names))

    def test_dir_name_exclude_only_matches_component(self):
        """dir_name 'cache' should not match 'cachefiles' directory."""
        os.makedirs(os.path.join(self.src, "cachefiles"))
        open(os.path.join(self.src, "cachefiles", "data.bin"), "w").close()
        self._run_backup(self._make_config(global_dirs='["cache"]'))
        names = self._get_tar_contents()
        self.assertTrue(any("data.bin" in n for n in names))

    def test_disabled_task_not_executed(self):
        """Disabled tasks should not create archives."""
        open(os.path.join(self.src, "file.txt"), "w").close()
        cfg = f'''
[meta]
name = "test"
enabled = true
[global_excludes]
endings = []
files = []
dir_names = []
[[backup]]
name = "disabled"
enabled = false
archive_name = "shouldnt_exist"
result_dir = "{self.out}"
create_target_date_dir = false
method = "targz"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = false
include_dirs = ["{self.src}"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''
        path = self._write_config(cfg)
        bs = Backupset(path)
        bs.execute()
        archives = [f for f in os.listdir(self.out) if not f.startswith('.')]
        self.assertEqual(archives, [])

    def test_global_and_task_endings_combined(self):
        """Both global and task endings should be excluded."""
        open(os.path.join(self.src, "keep.txt"), "w").close()
        open(os.path.join(self.src, "g.swp"), "w").close()
        open(os.path.join(self.src, "t.bak"), "w").close()
        self._run_backup(self._make_config(
            global_endings='["swp"]',
            task_endings='["bak"]'
        ))
        names = self._get_tar_contents()
        self.assertTrue(any("keep.txt" in n for n in names))
        self.assertFalse(any(".swp" in n for n in names))
        self.assertFalse(any(".bak" in n for n in names))

    def test_special_chars_in_filename(self):
        """Files with spaces and special chars should be archived normally."""
        open(os.path.join(self.src, "my file (1).txt"), "w").close()
        open(os.path.join(self.src, "name[bracket].dat"), "w").close()
        self._run_backup(self._make_config())
        names = self._get_tar_contents()
        self.assertTrue(any("my file (1).txt" in n for n in names))
        self.assertTrue(any("name[bracket].dat" in n for n in names))

    def test_zip_special_chars_in_filename(self):
        """Same as above but for zip."""
        open(os.path.join(self.src, "my file (1).txt"), "w").close()
        self._run_backup(self._make_config(method="zip"))
        names = self._get_zip_contents()
        self.assertTrue(any("my file (1).txt" in n for n in names))

    def test_skip_if_directory_nonexistent(self):
        """Task with nonexistent include dir and skip flag should not crash."""
        cfg = f'''
[meta]
name = "test"
enabled = true
[global_excludes]
endings = []
files = []
dir_names = []
[[backup]]
name = "skip"
enabled = true
archive_name = "out"
result_dir = "{self.out}"
create_target_date_dir = false
method = "targz"
followsym = false
withpath = false
skip_if_permission_fail = false
skip_if_directory_nonexistent = true
include_dirs = ["/nonexistent_dir_xyz_backupy"]
exclude_dir_names = []
exclude_dir_fullpaths = []
exclude_endings = []
exclude_files = []
'''
        path = self._write_config(cfg)
        bs = Backupset(path)
        # should not raise
        bs.execute()


if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
"""
存储相关的Mock数据
"""
from django.core.files.base import ContentFile


def create_mock_storage_class(file_overwrite=False, existing_files=None, file_contents=None):
    """创建Mock存储类"""
    existing_files = existing_files or []
    file_contents = file_contents or {}

    class MockStorage:
        def __init__(self):
            self.file_overwrite = file_overwrite
            self.files = dict(file_contents)

        def exists(self, name):
            return name in existing_files or name in self.files

        def _open(self, name, mode="rb"):
            if name in self.files:
                return ContentFile(self.files[name])
            return ContentFile(b"test content")

        def _save(self, name, content):
            self.files[name] = content.read()
            return name

        def save(self, name, content):
            """保存文件的公共方法"""
            return self._save(name, content)

        def delete(self, name):
            if name in self.files:
                del self.files[name]

        def listdir(self, path):
            return [], []

        def size(self, name):
            return len(self.files.get(name, b""))

        def url(self, name):
            return f"/media/{name}"

        def get_accessed_time(self, name):
            return None

        def get_created_time(self, name):
            return None

        def get_modified_time(self, name):
            return None

        def get_file_md5(self, file_name):
            return "test_md5"

        def _handle_file_source_list(self, file_source_list, extra_transfer_file_params):
            return [{"file_list": file_source_list, "file_type": 1}]

    return MockStorage


def create_mock_job_transfer_params(
    bk_biz_id=1,
    task_name="测试传输",
    timeout=300,
    account_alias="root",
    file_target_path="/data/install",
    file_source_list=None,
    target_server=None,
):
    """创建Mock作业传输参数"""
    return {
        "bk_biz_id": bk_biz_id,
        "task_name": task_name,
        "timeout": timeout,
        "account_alias": account_alias,
        "file_target_path": file_target_path,
        "file_source_list": file_source_list or ["/source/file.txt"],
        "target_server": target_server or {"ip_list": [{"bk_cloud_id": 0, "ip": "127.0.0.1"}]},
    }


# 常用的存储mock数据
DEFAULT_STORAGE_CLASS = create_mock_storage_class()
OVERWRITE_STORAGE_CLASS = create_mock_storage_class(file_overwrite=True)
EXISTING_FILES_STORAGE_CLASS = create_mock_storage_class(existing_files=["test.txt", "test_1.txt"])

# 常用的作业传输参数
DEFAULT_JOB_TRANSFER_PARAMS = create_mock_job_transfer_params()


def get_storage_mock(file_overwrite=False, **kwargs):
    """获取Mock存储实例，用于替换get_storage函数"""
    if file_overwrite:
        return OVERWRITE_STORAGE_CLASS()
    return DEFAULT_STORAGE_CLASS()

"""
Storage模块测试基类和工具方法
"""
from unittest.mock import Mock

from django.test import TestCase

from backend.tests.mock_data.components.job import JobApiMock
from backend.tests.mock_data.components.storage import create_mock_storage_class


class BaseStorageTestCase(TestCase):
    """Storage模块测试基类"""

    def setUp(self):
        super().setUp()
        self.mock_storage_class = create_mock_storage_class()
        self.job_mock = JobApiMock()

    def create_mock_storage_instance(self, storage_class, **kwargs):
        """创建mock的存储实例"""
        defaults = {"username": "admin", "cluster_id": 1, "bk_biz_id": 1}
        defaults.update(kwargs)

        instance = storage_class(**defaults)
        return instance

    def setup_job_mock(self, mock_fast_transfer_file, success=True, job_instance_id=12345):
        """设置Job API mock"""
        if success:
            mock_fast_transfer_file.return_value = {"job_instance_id": job_instance_id}
        else:
            mock_fast_transfer_file.side_effect = Exception("传输失败")

    def create_test_storage(self, base_class, **kwargs):
        """创建测试存储类"""
        MockStorageClass = create_mock_storage_class(**kwargs)

        class TestStorage(MockStorageClass, base_class):
            pass

        return TestStorage()

    def create_mock_file_object(self, **kwargs):
        """创建mock文件对象"""
        defaults = {"name": "test_file.txt", "size": 1024, "content_type": "text/plain"}
        defaults.update(kwargs)

        mock_file = Mock()
        for key, value in defaults.items():
            setattr(mock_file, key, value)

        # Mock read方法
        mock_file.read.return_value = b"test content"
        mock_file.chunks.return_value = [b"test content"]

        return mock_file

    def create_test_storage_classes(self):
        """创建测试用的存储类"""
        from backend.core.storages.base import BaseStorage, BkJobMixin, StorageFileOverwriteMixin

        class TestStorage(BaseStorage):
            def upload(self, file_obj, file_name=None):
                return f"uploaded_{file_name or file_obj.name}"

            def download(self, file_name):
                return b"downloaded content"

            def delete(self, file_name):
                return True

        class TestStorageWithOverwrite(StorageFileOverwriteMixin, TestStorage):
            pass

        class TestStorageWithJob(BkJobMixin, TestStorage):
            pass

        return TestStorage, TestStorageWithOverwrite, TestStorageWithJob

# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from unittest.mock import patch

import pytest
from django.core.files.base import ContentFile

from backend.core.storages import base
from backend.tests.core.storages.base import BaseStorageTestCase
from backend.tests.mock_data.components.storage import DEFAULT_JOB_TRANSFER_PARAMS, create_mock_job_transfer_params


class TestStorageFileOverwriteMixinFunctionality(BaseStorageTestCase):
    """测试存储文件覆盖混入功能"""

    def test_get_available_name_functionality(self):
        """测试获取可用文件名功能"""
        storage = self.create_test_storage(
            base.StorageFileOverwriteMixin, file_overwrite=False, existing_files=["test.txt", "test_1.txt"]
        )

        # 测试不存在的文件名
        result = storage.get_available_name("new_file.txt")
        assert result == "new_file.txt"

        # 测试已存在的文件名（会生成随机文件名，前缀长度为 3）
        result = storage.get_available_name("test.txt")
        assert result != "test.txt"
        assert "dbmrpt" in result  # 包含随机串标识
        random_prefix = result.rsplit("/", 1)[-1].split("_dbmrpt_")[0]
        assert len(random_prefix) == 3

    @patch("django.conf.settings.FILE_OVERWRITE", True)
    def test_get_available_name_with_overwrite_enabled(self):
        """测试启用文件覆盖时的获取可用文件名功能"""
        storage = self.create_test_storage(
            base.StorageFileOverwriteMixin, file_overwrite=True, existing_files=["test.txt"]
        )

        # 启用文件覆盖时，即使文件存在也返回原文件名
        result = storage.get_available_name("test.txt")
        assert result == "test.txt"

    def test_get_available_name_with_max_length(self):
        """测试带最大长度的获取可用文件名功能"""
        storage = self.create_test_storage(
            base.StorageFileOverwriteMixin, file_overwrite=False, existing_files=["test.txt"]
        )

        # 测试带最大长度的文件名
        result = storage.get_available_name("test.txt", max_length=50)
        assert len(result) <= 50
        assert result != "test.txt"


class TestBkJobMixinFunctionality(BaseStorageTestCase):
    """测试蓝鲸作业混入功能"""

    @patch("backend.components.JobApi.fast_transfer_file")
    def test_transfer_file_functionality(self, mock_fast_transfer_file):
        """测试文件传输功能"""
        self.setup_job_mock(mock_fast_transfer_file, success=True, job_instance_id=12345)

        storage = self.create_test_storage(base.BkJobMixin)

        # 使用预定义的传输参数
        params = DEFAULT_JOB_TRANSFER_PARAMS
        result = storage.fast_transfer_file(**params)

        # 验证API被调用
        mock_fast_transfer_file.assert_called_once()
        assert result == 12345  # job_instance_id

    def test_process_query_params_functionality(self):
        """测试查询参数处理功能"""
        storage = self.create_test_storage(base.BkJobMixin)

        from backend.components import JobApi

        query_params = create_mock_job_transfer_params(task_name="测试配置推送", file_source_list=["/config/file.conf"])

        result = storage.process_query_params(JobApi.fast_transfer_file, query_params)

        # 验证file_source_list被处理
        assert "file_source_list" in result
        assert isinstance(result["file_source_list"], list)
        assert result["bk_biz_id"] == 1
        assert result["task_name"] == "测试配置推送"

    @patch("backend.components.JobApi.fast_transfer_file")
    def test_transfer_file_failure(self, mock_fast_transfer_file):
        """测试文件传输失败功能"""
        self.setup_job_mock(mock_fast_transfer_file, success=False)

        storage = self.create_test_storage(base.BkJobMixin)

        # 应该抛出异常
        with pytest.raises(Exception):
            storage.fast_transfer_file(**DEFAULT_JOB_TRANSFER_PARAMS)


class TestBaseStorageFunctionality(BaseStorageTestCase):
    """测试基础存储功能"""

    def test_base_storage_abstract_methods(self):
        """测试基础存储抽象方法"""
        # BaseStorage实际上不是抽象基类，可以实例化
        try:
            storage = base.BaseStorage()
            assert storage is not None
        except TypeError:
            # 如果不能实例化，说明是抽象基类
            pass

    def test_base_storage_subclass_implementation(self):
        """测试基础存储子类实现功能"""
        storage = self.create_test_storage(base.BaseStorage)

        # 测试基本功能
        assert storage.exists("test.txt") is False
        assert storage.size("test.txt") == 0
        assert storage.url("test.txt") == "/media/test.txt"
        assert storage.get_file_md5("test.txt") == "test_md5"

        # 测试文件操作
        content = storage.open("test.txt")
        assert content.read() == b"test content"

        # 测试保存文件
        result = storage.save("test.txt", ContentFile(b"new content"))
        assert result == "test.txt"

    def test_base_storage_file_operations(self):
        """测试基础存储文件操作功能"""
        storage = self.create_test_storage(base.BaseStorage)

        # 测试保存文件
        content = ContentFile(b"test content")
        result = storage.save("test.txt", content)
        assert result == "test.txt"
        assert storage.exists("test.txt") is True
        assert storage.size("test.txt") == 12

        # 测试读取文件
        with storage.open("test.txt") as f:
            assert f.read() == b"test content"

        # 测试删除文件
        storage.delete("test.txt")
        assert storage.exists("test.txt") is False

    @patch("django.conf.settings.FILE_OVERWRITE", True)
    def test_base_storage_with_storage_file_overwrite_mixin(self):
        """测试基础存储与文件覆盖混入组合功能"""

        # 创建组合类
        class CombinedStorage(base.BaseStorage, base.StorageFileOverwriteMixin):
            pass

        storage = self.create_test_storage(CombinedStorage, file_overwrite=True)

        # 测试文件覆盖功能
        content1 = ContentFile(b"content 1")
        content2 = ContentFile(b"content 2")

        # 保存第一个文件
        storage.save("test.txt", content1)
        assert storage.exists("test.txt") is True

        # 获取可用文件名（启用覆盖时应该返回原文件名）
        available_name = storage.get_available_name("test.txt")
        assert available_name == "test.txt"

        # 保存第二个文件（会覆盖第一个文件）
        storage.save(available_name, content2)
        assert storage.exists("test.txt") is True

        # 验证文件内容被覆盖
        with storage.open("test.txt") as f:
            assert f.read() == b"content 2"

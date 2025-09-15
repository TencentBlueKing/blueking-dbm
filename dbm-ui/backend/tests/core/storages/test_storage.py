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
import os
import tempfile
from unittest.mock import Mock, patch

import pytest
from django.core.files.base import ContentFile

from backend.core.storages import constants
from backend.core.storages.storage import (
    AdminFileSystemStorage,
    CustomBKRepoStorage,
    MyBKGenericRepoClient,
    cache_storage_obj,
    get_storage,
)

pytestmark = pytest.mark.django_db


class TestMyBKGenericRepoClient:
    """测试MyBKGenericRepoClient核心功能"""

    def test_list_dir(self):
        """测试list_dir分页查询"""
        client = MyBKGenericRepoClient(
            bucket="test-bucket",
            project="test-project",
            username="admin",
            password="password",
            endpoint_url="http://test.com",
        )

        mock_dirs = [{"name": "dir1", "folder": True}]
        mock_files = [{"name": "file1.txt", "folder": False}]

        with patch.object(
            client,
            "_MyBKGenericRepoClient__list_dir",
            side_effect=[(mock_dirs, mock_files, False)],
        ):
            directories, files = client.list_dir("/test/")
            assert len(directories) == 1
            assert len(files) == 1

    def test_list_dir_multiple_pages(self):
        """测试list_dir多页查询"""
        client = MyBKGenericRepoClient(
            bucket="test-bucket",
            project="test-project",
            username="admin",
            password="password",
            endpoint_url="http://test.com",
        )

        with patch.object(
            client,
            "_MyBKGenericRepoClient__list_dir",
            side_effect=[
                ([{"name": "dir1", "folder": True}], [{"name": "file1.txt", "folder": False}], True),
                ([{"name": "dir2", "folder": True}], [{"name": "file2.txt", "folder": False}], False),
            ],
        ):
            directories, files = client.list_dir("/test/")
            assert len(directories) == 2
            assert len(files) == 2

    def test_build_download_url(self):
        """测试构造下载url"""
        client = MyBKGenericRepoClient(
            bucket="test-bucket",
            project="test-project",
            username="admin",
            password="password",
            endpoint_url="http://test.com",
        )

        url = client.build_download_url("/path/to/file.txt", force_download=False)
        assert "test-project" in url
        assert "test-bucket" in url
        assert "download=false" in url

    @patch("backend.core.storages.storage.curlify.to_curl")
    def test_batch_download(self, mock_to_curl):
        """测试批量下载"""
        client = MyBKGenericRepoClient(
            bucket="test-bucket",
            project="test-project",
            username="admin",
            password="password",
            endpoint_url="http://test.com",
        )

        mock_response = Mock()
        mock_response.ok = True
        mock_response.request = Mock()
        mock_response.request.headers = {}
        mock_get = Mock(return_value=mock_response)
        mock_to_curl.return_value = "curl ..."

        with patch.object(client, "get_client") as mock_get_client:
            mock_get_client.return_value.get = mock_get
            result = client.batch_download(["/file1.txt", "/file2.txt"])
            assert result == mock_response


class TestCustomBKRepoStorage:
    """测试CustomBKRepoStorage核心功能"""

    @patch("backend.core.storages.storage.bkrepo.BKRepoStorage.__init__")
    @patch("backend.core.storages.storage.settings")
    def test_batch_download(self, mock_settings, mock_bkrepo_init):
        """测试批量下载"""
        mock_settings.BKREPO_USERNAME = "admin"
        mock_settings.BKREPO_PASSWORD = "password"
        mock_settings.BKREPO_PROJECT = "test-project"
        mock_settings.BKREPO_BUCKET = "test-bucket"
        mock_settings.BKREPO_ENDPOINT_URL = "http://test.com"
        mock_settings.FILE_OVERWRITE = False
        mock_bkrepo_init.return_value = None

        storage = CustomBKRepoStorage()
        mock_response = Mock()

        with patch.object(storage.client, "batch_download", return_value=mock_response):
            result = storage.batch_download(["/file1.txt", "/file2.txt"])
            assert result == mock_response

    @patch("backend.core.storages.storage.bkrepo.BKRepoStorage.__init__")
    @patch("backend.core.storages.storage.settings")
    def test_download_url_public(self, mock_settings, mock_bkrepo_init):
        """测试公共仓库下载url"""
        mock_settings.BKREPO_USERNAME = "admin"
        mock_settings.BKREPO_PASSWORD = "password"
        mock_settings.BKREPO_PROJECT = "test-project"
        mock_settings.BKREPO_BUCKET = "test-bucket"
        mock_settings.BKREPO_ENDPOINT_URL = "http://test.com"
        mock_settings.FILE_OVERWRITE = False
        mock_bkrepo_init.return_value = None

        storage = CustomBKRepoStorage()
        storage.client.is_public = True

        with patch.object(storage, "_full_path", return_value="/full/path/file.txt"):
            with patch.object(storage.client, "build_download_url", return_value="http://download.url"):
                url = storage.download_url("file.txt", force_download=True)
                assert url == "http://download.url"


class TestAdminFileSystemStorage:
    """测试AdminFileSystemStorage核心功能"""

    def test_path(self):
        """测试path方法"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = AdminFileSystemStorage(location=temp_dir)
            path = storage.path("test.txt")
            assert path == os.path.join(temp_dir, "test.txt")

    def test_get_file_md5(self):
        """测试获取文件md5"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = AdminFileSystemStorage(location=temp_dir)

            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")

            md5_value = storage.get_file_md5(test_file)
            assert isinstance(md5_value, str)
            assert len(md5_value) == 32

    def test_save_with_overwrite(self):
        """测试保存文件并覆盖"""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = AdminFileSystemStorage(location=temp_dir, file_overwrite=True)

            # 保存第一个文件
            content1 = ContentFile(b"content 1")
            name = storage.save("test.txt", content1)
            assert name == "test.txt"

            # 保存第二个文件（覆盖第一个）
            content2 = ContentFile(b"content 2")
            name = storage.save("test.txt", content2)
            assert name == "test.txt"

            # 验证文件内容被覆盖
            with storage.open("test.txt") as f:
                assert f.read() == b"content 2"


class TestCacheStorageObj:
    """测试cache_storage_obj装饰器"""

    def test_cache_storage_obj_basic(self):
        """测试基础缓存功能"""

        @cache_storage_obj
        def mock_get_storage(storage_type=None, **kwargs):
            return Mock(storage_type=storage_type)

        # 第一次调用，会缓存
        storage1 = mock_get_storage("test_type")
        # 第二次调用，返回缓存
        storage2 = mock_get_storage("test_type")
        assert storage1 is storage2


class TestGetStorage:
    """测试get_storage函数"""

    @patch("backend.core.storages.storage.settings")
    @patch("backend.core.storages.storage.get_storage_class")
    def test_get_storage_default(self, mock_get_storage_class, mock_settings):
        """测试获取默认storage"""
        mock_settings.STORAGE_TYPE = constants.StorageType.FILE_SYSTEM.value
        mock_settings.STORAGE_TYPE_IMPORT_PATH_MAP = {
            constants.StorageType.FILE_SYSTEM.value: "backend.core.storages.storage.AdminFileSystemStorage"
        }

        mock_storage_class = Mock()
        mock_get_storage_class.return_value = mock_storage_class

        with tempfile.TemporaryDirectory() as temp_dir:
            get_storage(location=temp_dir)
            mock_storage_class.assert_called_once()

    @patch("backend.core.storages.storage.settings")
    @patch("backend.core.storages.storage.get_storage_class")
    def test_get_storage_safe_mode(self, mock_get_storage_class, mock_settings):
        """测试安全模式"""
        mock_settings.STORAGE_TYPE = constants.StorageType.FILE_SYSTEM.value
        mock_settings.STORAGE_TYPE_IMPORT_PATH_MAP = {
            constants.StorageType.FILE_SYSTEM.value: "backend.core.storages.storage.AdminFileSystemStorage"
        }

        mock_storage_class = Mock()
        mock_storage_class.safe_class = Mock()
        mock_get_storage_class.return_value = mock_storage_class

        get_storage(safe=True)
        mock_storage_class.safe_class.assert_called_once()

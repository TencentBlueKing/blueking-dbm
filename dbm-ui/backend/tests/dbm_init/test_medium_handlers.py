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
import hashlib
import sys
import types
from unittest.mock import Mock, patch

from backend.dbm_init.medium.handlers import MediumHandler

ACTUATOR_INFO = {
    "buildPath": "",
    "name": "dbactuator",
    "version": "1.0.4",
    "distribution_name": "DBM",
    "version_series": "dbactuator",
    "full_version": "1.0.5",
    "os_type": "Linux",
}
LOCK_INFO = {"es": [{"actuator": ACTUATOR_INFO}]}
FORMAL_DIR = "/es/actuator/DBM/1.0.5.0.0.0"


def patch_lock(lock_info=None):
    return patch.object(MediumHandler, "_MediumHandler__load_medium_lock", return_value=lock_info or LOCK_INFO)


class TestMediumFormalDir:
    def test_format_full_version(self):
        assert MediumHandler.medium_formal_dir("es", "actuator", ACTUATOR_INFO) == FORMAL_DIR

    def test_default_distribution_and_version(self):
        info = {"name": "dbha", "version": "1.0.2"}

        assert MediumHandler.medium_formal_dir("cloud", "cloud-dbha", info) == "/cloud/cloud-dbha/DBM/1.0.2.0.0.0"


class TestBuildMedium:
    def test_copy_to_formal_dir(self, tmp_path):
        build_file = tmp_path / "dbactuator"
        build_file.write_bytes(b"bin")
        lock_info = {"es": [{"actuator": {**ACTUATOR_INFO, "buildPath": str(build_file)}}]}

        with patch_lock(lock_info):
            MediumHandler.build_medium(bkrepo_tmp_dir=str(tmp_path / "medium"))

        assert (tmp_path / "medium" / FORMAL_DIR.lstrip("/") / "dbactuator").read_bytes() == b"bin"

    def test_skip_missing_build_file(self, tmp_path):
        lock_info = {"es": [{"actuator": {**ACTUATOR_INFO, "buildPath": str(tmp_path / "not_exist")}}]}

        with patch_lock(lock_info):
            MediumHandler.build_medium(bkrepo_tmp_dir=str(tmp_path / "medium"))

        assert not (tmp_path / "medium").exists()


class TestUploadMedium:
    def _prepare(self, tmp_path):
        medium_dir = tmp_path / "medium"
        target_dir = medium_dir / FORMAL_DIR.lstrip("/")
        target_dir.mkdir(parents=True)
        (target_dir / "dbactuator").write_bytes(b"bin")
        # 不在 medium.lock 中的文件不应上传
        (target_dir / "init.sql").write_bytes(b"sql")
        return str(medium_dir), hashlib.md5(b"bin").hexdigest()

    def test_upload_lock_medium_only(self, tmp_path):
        medium_dir, _ = self._prepare(tmp_path)
        storage = Mock()
        storage.listdir.return_value = ([], [{"name": "other_exporter.tgz", "md5": "x"}])

        with patch_lock():
            MediumHandler(storage=storage).upload_medium(path="", bkrepo_tmp_dir=medium_dir)

        storage.listdir.assert_called_once_with(FORMAL_DIR)
        storage.save.assert_called_once()
        assert storage.save.call_args[0][0] == f"{FORMAL_DIR.lstrip('/')}/dbactuator"

    def test_skip_when_md5_equal(self, tmp_path):
        medium_dir, md5 = self._prepare(tmp_path)
        storage = Mock()
        storage.listdir.return_value = ([], [{"name": "dbactuator", "md5": md5}])

        with patch_lock():
            MediumHandler(storage=storage).upload_medium(path="", bkrepo_tmp_dir=medium_dir)

        storage.save.assert_not_called()

    def test_skip_other_db_type_and_missing_file(self, tmp_path):
        medium_dir, _ = self._prepare(tmp_path)
        lock_info = {**LOCK_INFO, "redis": [{"actuator": {**ACTUATOR_INFO, "name": "dbactuator_redis"}}]}
        storage = Mock()
        storage.listdir.return_value = ([], [])

        with patch_lock(lock_info):
            MediumHandler(storage=storage).upload_medium(path="redis", bkrepo_tmp_dir=medium_dir)

        storage.save.assert_not_called()


class TestSyncFromBkrepo:
    def test_sync_formal_dir_media(self):
        media = {
            "name": "dbactuator",
            "fullPath": f"{FORMAL_DIR}/dbactuator",
            "size": 3,
            "md5": "md5",
            "createdDate": "2026-09-23T10:00:00",
            "lastModifiedDate": "2026-09-23T10:00:00",
        }
        tree = {
            # sqlfile 不在 medium.lock 中，不应被下钻
            "/es": (
                [{"name": "actuator", "fullPath": "/es/actuator"}, {"name": "sqlfile", "fullPath": "/es/sql"}],
                [],
            ),
            # 1.0.4 为旧版 4 级目录，其下只有文件没有子目录，应被跳过
            "/es/actuator": (
                [{"name": "DBM", "fullPath": "/es/actuator/DBM"}, {"name": "1.0.4", "fullPath": "/x"}],
                [],
            ),
            "/es/actuator/DBM": ([{"name": "1.0.5.0.0.0", "fullPath": FORMAL_DIR}], []),
            FORMAL_DIR: ([], [media]),
            "/x": ([], []),
        }
        storage = Mock()
        storage.listdir.side_effect = lambda path: tree[path]
        http = Mock()
        network = types.ModuleType("network")
        network.HttpHandler = Mock(return_value=http)

        with patch_lock(), patch.dict(sys.modules, {"network": network}):
            MediumHandler(storage=storage).sync_from_bkrepo(db_type="es")

        infos = http.post.call_args[1]["data"]["sync_medium_infos"]
        assert len(infos) == 1
        assert infos[0]["path"] == f"{FORMAL_DIR}/dbactuator"
        assert infos[0]["version"] == "1.0.4"
        assert infos[0]["full_version"] == "1.0.5.0.0.0"
        assert infos[0]["version_series"] == "dbactuator"


class TestCollectMonitorPlugins:
    def test_exporter_path_uses_formal_dir(self):
        plugins = MediumHandler(storage=Mock())._collect_monitor_plugins()

        assert plugins["dbm_elasticsearch_exporter"]["bkrepo_path"] == (
            "/es/exporter/DBM/1.0.0.0.0.0/dbm_elasticsearch_exporter.tgz"
        )

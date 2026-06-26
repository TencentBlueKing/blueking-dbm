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
from unittest.mock import Mock

import pytest

from backend.core.storages.exceptions import StagingFileError
from backend.core.storages.handlers import StorageHandler

STAGING_PATH = "/staging/mysql/actuator/DBM/1790153031593/dbactuator"
FORMAL_PATH = "/mysql/actuator/DBM/1.0.5.0.0.0/dbactuator"


def build_handler(existing_paths):
    storage = Mock()
    storage.exists.side_effect = lambda path: path in existing_paths
    return StorageHandler(storage=storage), storage


class TestMoveStagingFileToFormal:
    def test_move_to_given_formal_path(self):
        handler, storage = build_handler({STAGING_PATH})

        assert handler.move_staging_file_to_formal(STAGING_PATH, FORMAL_PATH) == FORMAL_PATH
        storage.client.move_file.assert_called_once_with(STAGING_PATH, FORMAL_PATH, overwrite=True)

    def test_non_staging_path_returned_as_is(self):
        handler, storage = build_handler(set())

        assert handler.move_staging_file_to_formal(FORMAL_PATH, "/any/path/dbactuator") == FORMAL_PATH
        storage.client.move_file.assert_not_called()

    def test_already_moved_is_idempotent(self):
        handler, storage = build_handler({FORMAL_PATH})

        assert handler.move_staging_file_to_formal(STAGING_PATH, FORMAL_PATH) == FORMAL_PATH
        storage.client.move_file.assert_not_called()

    def test_missing_everywhere_raises(self):
        handler, _ = build_handler(set())

        with pytest.raises(StagingFileError):
            handler.move_staging_file_to_formal(STAGING_PATH, FORMAL_PATH)

    @pytest.mark.parametrize(
        "staging_path,formal_path",
        [
            ("/staging/mysql/actuator/../x/dbactuator", FORMAL_PATH),
            (STAGING_PATH, "/mysql/actuator/DBM/../dbactuator"),
            (STAGING_PATH, "/mysql/actuator/DBM/1.0.5.0.0.0/other"),
            (STAGING_PATH, "/staging/mysql/actuator/DBM/1.0.5.0.0.0/dbactuator"),
            (STAGING_PATH, ""),
        ],
    )
    def test_invalid_path_raises(self, staging_path, formal_path):
        handler, storage = build_handler({staging_path})

        with pytest.raises(StagingFileError):
            handler.move_staging_file_to_formal(staging_path, formal_path)
        storage.client.move_file.assert_not_called()

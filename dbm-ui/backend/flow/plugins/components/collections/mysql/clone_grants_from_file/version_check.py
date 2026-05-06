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

import re

from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class CloneGrantsVersionCheckService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        source_raw_version = kwargs["source_raw_version"]
        dest_addresses = kwargs["dest_addresses"]
        bk_cloud_id = kwargs["bk_cloud_id"]
        is_spider = kwargs["is_spider"]

        if is_spider:
            source_main_version = self._get_spider_main_version(source_raw_version)
        else:
            source_main_version = self._get_mysql_main_version(source_raw_version)

        res = DRSApi.rpc(
            {
                "addresses": dest_addresses,
                "cmds": ["select @@version as version"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )

        bad_dest_versions = []
        for ele in res:
            if ele["error_msg"]:
                self.log_error(f"check source version failed: {ele['error_msg']}")
                return False

            if ele["cmd_results"][0]["error_msg"]:
                self.log_error(f"check source version failed: {ele['cmd_results'][0]['error_msg']}")
                return False

            addr = ele["address"]
            raw_version = ele["cmd_results"][0]["table_data"][0]["version"]
            if is_spider:
                main_version = self._get_spider_main_version(raw_version)
            else:
                main_version = self._get_mysql_main_version(raw_version)

            if main_version < source_main_version:
                bad_dest_versions.append({"address": addr, "raw_version": raw_version, "main_version": main_version})

        if bad_dest_versions:
            self.log_error(f"source versions higher than dest({source_main_version}): {bad_dest_versions}")
            return False

        return True

    @staticmethod
    def _get_spider_main_version(raw_version: str) -> int:
        """Extract tspider major version from raw version string like '5.5.24-tspider-1.13-log' -> 1"""
        m = re.search(r"-tspider-(\d+)\.\d+", raw_version)
        if not m:
            raise ValueError(f"cannot parse tspider version from '{raw_version}'")
        return int(m.group(1))

    @staticmethod
    def _get_mysql_main_version(raw_version: str) -> int:
        """Extract mysql major+minor as int from raw version string like '5.7.20-tmysql-3.3-log' -> 57"""
        m = re.match(r"(\d+)\.(\d+)", raw_version)
        if not m:
            raise ValueError(f"cannot parse mysql version from '{raw_version}'")
        return int(m.group(1)) * 10 + int(m.group(2))


class CloneGrantsVersionCheckComponent(Component):
    name = __name__
    code = "clone_grants_version_check"
    bound_service = CloneGrantsVersionCheckService

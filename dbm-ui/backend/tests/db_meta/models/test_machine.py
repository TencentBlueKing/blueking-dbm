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
import base64
import gzip
import json
from unittest.mock import patch

import pytest

from backend.db_meta import api
from backend.db_meta.models import Cluster, Machine
from backend.tests.db_meta.api.dbha.test_apis import TEST_PROXY_PORT1, TEST_PROXY_PORT2
from backend.tests.mock_data.components import cc
from backend.tests.mock_data.components.cc import CCApiMock

pytestmark = pytest.mark.django_db


class TestMachine:
    @patch("backend.db_meta.models.app.CCApi", CCApiMock())
    def test_dbm_meta(self, init_proxy_machine, init_cluster):
        machine = Machine.objects.first()
        cluster = Cluster.objects.first()
        proxy_objs = api.proxy_instance.create(
            [
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT1,
                },
                {
                    "ip": cc.NORMAL_IP,
                    "port": TEST_PROXY_PORT2,
                },
            ]
        )
        cluster.proxyinstance_set.add(*proxy_objs)
        dbm_meta = machine.dbm_meta
        assert dbm_meta == {
            "version": "v2",
            "content": "H4sIAAAAAAAC/9WOSwoCMRBErzL0WobMgBuvIjLkJwaTdEwiTAi5u90uRI9gr6rrFUV10BgCRjhNfRwm0"
            "M9SMdB37iBTIgFANkln+FmFOAq+lW3tKW7zZjBIxx1wlXc7GzVT63egtmQZVxuNuklGRn3c0MrDs+diqT"
            "Jqu2X0b5Iy7u2HJMyVyUIbFqDJf7BTwLiMF+mlgLRqAQAA",
        }

        # 将Base64字符串解码回压缩的字节数据
        compressed_bytes_from_base64 = base64.b64decode(dbm_meta["content"])

        # 使用gzip解压缩
        decompressed_bytes = gzip.decompress(compressed_bytes_from_base64)

        # 将解压缩的字节解码回原始字符串
        decompressed_string = decompressed_bytes.decode("utf-8")
        dbm_meta_content = json.loads(decompressed_string)
        assert dbm_meta_content == {
            "common": {},
            "custom": [
                {
                    "app": "",
                    "appid": "2005000002",
                    "cluster_domain": "fake.db.com",
                    "cluster_type": "tendbha",
                    "db_type": "mysql",
                    "instance_role": "proxy",
                    "instance_port": "10001",
                },
                {
                    "app": "",
                    "appid": "2005000002",
                    "cluster_domain": "fake.db.com",
                    "cluster_type": "tendbha",
                    "db_type": "mysql",
                    "instance_role": "proxy",
                    "instance_port": "10000",
                },
            ],
        }

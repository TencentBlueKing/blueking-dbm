"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict

from backend.components import DRSApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import DEFAULT_REDIS_DBNUM
from backend.flow.utils.base.payload_handler import PayloadHandler

"""
Redis CLIENT LIST 和 COMMAND STATS 业务逻辑实现
"""


class RedisClientListService:
    """Redis客户端查询服务"""

    def __init__(self, addr: str, immute_domain: str):
        """
        初始化Redis连接
        """
        self.addr = addr
        self.cluster_obj = Cluster.objects.get(immute_domain=immute_domain)
        self.bk_cloud_id = self.cluster_obj.bk_cloud_id
        self.machine_obj = Machine.objects.get(bk_cloud_id=self.bk_cloud_id, ip=addr.split(":")[0])
        passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(self.cluster_obj.id)

        if self.machine_obj.access_layer == AccessLayer.PROXY.value:
            self.instance_password = passwd_ret.get("redis_proxy_password")
        else:
            self.instance_password = passwd_ret.get("redis_password")

    def get_client_list(self) -> Dict:
        """
        获取Redis客户端列表

        Returns:
            包含客户端总数和客户端列表的字典
        """
        # 执行 CLIENT LIST 命令
        result = {}
        resp = DRSApi.redis_rpc(
            {
                "addresses": [self.addr],
                "db_num": DEFAULT_REDIS_DBNUM,
                "password": self.instance_password,
                "command": "CLIENT LIST",
                "bk_cloud_id": self.bk_cloud_id,
            }
        )
        if not resp or len(resp) == 0:
            return result
        client_list_str = resp[0].get("result")

        # 解析客户端列表
        clients = []
        if isinstance(client_list_str, str):
            # 按行分割
            lines = client_list_str.strip().split("\n")
            for line in lines:
                if not line.strip():
                    continue

                # 解析每个客户端的信息
                client_info = self._parse_client_info(line)
                if client_info:
                    clients.append(client_info)
        elif isinstance(client_list_str, list):
            # 新版本redis-py可能直接返回列表
            for client_dict in client_list_str:
                client_info = self._normalize_client_info(client_dict)
                if client_info:
                    clients.append(client_info)

        return {"total_clients": len(clients), "clients": clients}

    def _parse_client_info(self, line: str) -> Dict:
        """
        解析单个客户端信息行
        """
        client_info = {}
        parts = line.split()

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                client_info[key] = value

        # 标准化字段
        return self._normalize_client_info(client_info)

    def _normalize_client_info(self, raw_info: Dict) -> Dict:
        """
        标准化客户端信息字段
        """

        def safe_int(value, default=0):
            try:
                return int(value)
            except (ValueError, TypeError):
                return default

        return {
            "id": str(raw_info.get("id", "")),
            "addr": str(raw_info.get("addr", "")),
            "fd": safe_int(raw_info.get("fd")),
            "name": str(raw_info.get("name", "")),
            "age": safe_int(raw_info.get("age")),
            "idle": safe_int(raw_info.get("idle")),
            "flags": str(raw_info.get("flags", "")),
            "db": safe_int(raw_info.get("db")),
            "sub": safe_int(raw_info.get("sub")),
            "psub": safe_int(raw_info.get("psub")),
            "multi": safe_int(raw_info.get("multi")),
            "qbuf": safe_int(raw_info.get("qbuf")),
            "qbuf_free": safe_int(raw_info.get("qbuf-free")),
            "obl": safe_int(raw_info.get("obl")),
            "oll": safe_int(raw_info.get("oll")),
            "omem": safe_int(raw_info.get("omem")),
            "events": str(raw_info.get("events", "")),
            "cmd": str(raw_info.get("cmd", "")),
        }

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
import logging.config
from typing import Dict, List, Tuple

from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_predixy_proxy_type, is_twemproxy_proxy_type
from backend.flow.consts import ConfigTypeEnum

logger = logging.getLogger("flow")


class TwemproxyBackendItem:
    def __init__(self, addr: str, app: str, seg_start: int, seg_end: int, weight: int):
        self.addr = addr
        self.app = app
        self.segment_start = seg_start
        self.segment_end = seg_end
        self.weight = weight

    # String 用于打印
    def __str__(self):
        return f"{self.addr} {self.app} {self.segment_start}-{self.segment_end} {self.weight}"

    # StringWithoutApp 不带app信息
    def string_without_app(self):
        return f"{self.addr} {self.segment_start}-{self.segment_end} {self.weight}"

    # StringWithoutWeight
    def string_without_weight(self):
        return f"{self.addr} {self.app} {self.segment_start}-{self.segment_end}"


def decode_twemproxy_backends(backends_str: str) -> Tuple[List[TwemproxyBackendItem], Dict[str, TwemproxyBackendItem]]:
    backend_list = []
    backend_addr_map = {}
    backends_str = backends_str.strip()
    lines = backends_str.split("\n")
    for line in lines:
        line = line.strip()
        list01 = line.split()
        if len(list01) != 4:
            err = f"twemproxy backend:{line} format not correct"
            raise ValueError(err)
        backend_item = TwemproxyBackendItem(
            addr=list01[0],
            app=list01[1],
            seg_start=int(list01[2].split("-")[0]),
            seg_end=int(list01[2].split("-")[1]),
            weight=int(list01[3]),
        )
        backend_list.append(backend_item)
        backend_addr_map[backend_item.addr] = backend_item
    return backend_list, backend_addr_map


class PredixyInfoServer:
    """
    predixy info server项
    """

    def __init__(self):
        self.server = ""
        self.role = ""
        self.group = ""
        self.dc = ""
        self.current_is_fail = 0
        self.connections = 0
        self.connect = 0
        self.requests = 0
        self.responses = 0
        self.send_bytes = 0
        self.recv_bytes = 0

    def __str__(self):
        return f"Server:{self.server} Role:{self.role} Group:{self.group} DC:{self.dc}"


def decode_predixy_info_servers(info_str):
    """
    解析predixy info servers
    """
    rets = []
    info_list = info_str.split("\n")
    item = PredixyInfoServer()
    for info_item in info_list:
        info_item = info_item.strip()
        if info_item.startswith("#"):
            continue
        if len(info_item) == 0:
            if item.server != "":
                rets.append(item)
                item = PredixyInfoServer()
            continue
        list01 = info_item.split(":", 2)
        if len(list01) < 2:
            continue
        if list01[0] == "Server":
            item.server = list01[1]
        elif list01[0] == "Role":
            item.role = list01[1]
        elif list01[0] == "Group":
            item.group = list01[1]
        elif list01[0] == "DC":
            item.dc = list01[1]
        elif list01[0] == "CurrentIsFail":
            item.current_is_fail = int(list01[1])
        elif list01[0] == "Connections":
            item.connections = int(list01[1])
        elif list01[0] == "Connect":
            item.connect = int(list01[1])
        elif list01[0] == "Requests":
            item.requests = int(list01[1])
        elif list01[0] == "Responses":
            item.responses = int(list01[1])
        elif list01[0] == "SendBytes":
            item.send_bytes = int(list01[1])
        elif list01[0] == "RecvBytes":
            item.recv_bytes = int(list01[1])
    return rets


def check_cluster_proxy_backends_consistent(cluster_id: int, cluster_password: str):
    cluster: Cluster = None
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise Exception("src_cluster {} does not exist".format(cluster_id))

    if cluster_password == "":
        proxy_conf = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(cluster.db_module_id)},
                "conf_file": cluster.proxy_version,
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP,
            }
        )
        proxy_content = proxy_conf.get("content", {})
        cluster_password = proxy_content.get("password", "")

    proxy_addrs = []
    proxys_backend_md5 = []
    if is_twemproxy_proxy_type(cluster.cluster_type):
        # twemproxy 集群
        for proxy in cluster.proxyinstance_set.all():
            proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port + 1000))
        resp = DRSApi.twemproxy_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": 0,
                "password": "",
                "command": "get nosqlproxy servers",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for ele in resp:
            backends_ret, _ = decode_twemproxy_backends(ele["result"])
            sorted_backends = sorted(backends_ret, key=lambda x: x.segment_start)
            sorted_str = ""
            for bck in sorted_backends:
                sorted_str += bck.string_without_app() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
    elif is_predixy_proxy_type(cluster.cluster_type):
        # predixy 集群
        for proxy in cluster.proxyinstance_set.all():
            proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port))
        resp = DRSApi.redis_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": 0,
                "password": cluster_password,
                "command": "info servers",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for ele in resp:
            backends_ret = decode_predixy_info_servers(ele["result"])
            sorted_backends = sorted(backends_ret, key=lambda x: x.server)
            sorted_str = ""
            for bck in sorted_backends:
                sorted_str += bck.__str__() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
    # 检查md5是否一致
    sorted_md5 = sorted(proxys_backend_md5, key=lambda x: x["backend_md5"])
    if sorted_md5[0]["backend_md5"] != sorted_md5[-1]["backend_md5"]:
        logger.error(
            "proxy[{}->{}] backends is not same".format(sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"])
        )
        raise Exception(
            "proxy[{}->{}] backends is not same".format(sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"])
        )

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
from typing import Dict, List, Tuple


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

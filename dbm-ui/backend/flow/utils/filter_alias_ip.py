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
from typing import Dict, List


class FilterAliasMixins(object):
    def filter_alone_alias_ip(self, instances: List, clusters: List):
        for cluster in clusters:
            for inst in instances:
                if cluster["item"] == inst["ip"]:
                    inst["ip"] = cluster["data"][0]["ip"]
        return instances

    def filter_cluster_alias_ip(self, inst: Dict, clusters: List):
        proxies = inst.get("proxies")
        storages = inst.get("storages")
        storage = inst.get("storage")
        for cluster in clusters:
            if proxies:
                for proxy in proxies:
                    if proxy["ip"] == cluster["item"]:
                        proxy["ip"] = cluster["data"][0]["ip"]

            if storages:
                for storage in storages:
                    if storage["ip"] == cluster["item"]:
                        storage["ip"] = cluster["data"][0]["ip"]

            if storage:
                if storage["ip"] == cluster["item"]:
                    storage["ip"] = cluster["data"][0]["ip"]
        return inst

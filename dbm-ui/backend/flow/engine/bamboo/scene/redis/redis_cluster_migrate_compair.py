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
import logging.config
from collections import defaultdict
from typing import Dict, Optional

from backend.db_meta import api
from backend.db_meta.models import CLBEntryDetail, Cluster

logger = logging.getLogger("flow")


class RedisClusterMigrateCompairFlow(object):
    """
    迁移后数据对比
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __check(self, data: dict):
        for param in data["clusters"]:
            # 处理input
            input_seg_dict = defaultdict(dict)
            input_proxy_list = []
            for backend in param["backends"]:
                input_seg_dict[backend["shard"]] = {
                    "master": "{}:{}".format(backend["nodes"]["master"]["ip"], backend["nodes"]["master"]["port"]),
                    "slave": "{}:{}".format(backend["nodes"]["slave"]["ip"], backend["nodes"]["slave"]["port"]),
                }
            for proxy in param["proxies"]:
                input_proxy_list.append("{}:{}".format(proxy["ip"], proxy["port"]))

            # 获取db元数据
            domain = param["clusterinfo"]["immute_domain"]
            c = Cluster.objects.get(immute_domain=domain)
            cluster = api.cluster.nosqlcomm.other.get_cluster_detail(c.id)[0]
            db_proxy_list = cluster["twemproxy_set"]
            redis_master_set = cluster["redis_master_set"]
            redis_slave_set = cluster["redis_slave_set"]
            db_seg_dict = defaultdict(dict)
            for node_info in redis_master_set:
                ins = str.split(node_info, " ")[0]
                seg = str.split(node_info, " ")[1]
                db_seg_dict[seg]["master"] = ins
            for node_info in redis_slave_set:
                ins = str.split(node_info, " ")[0]
                seg = str.split(node_info, " ")[1]
                db_seg_dict[seg]["slave"] = ins
            self.__check_machine(input_proxy_list, input_seg_dict, db_proxy_list, db_seg_dict)

            if param["entry"]["clb"]:
                clb_ip = cluster["clusterentry_set"]["clbDns"][0]
                clb_info = CLBEntryDetail.objects.filter(clb_ip=clb_ip).values()[0]
                db_clb = {
                    "ip": clb_ip,
                    "id": clb_info["clb_id"],
                    "listener_id": clb_info["listener_id"],
                    "region": clb_info["clb_region"],
                }
                # clb_domain属于域名检查项，不在这里检查
                param["entry"]["clb"].pop("clb_domain", None)
                self.__check_dict_info(param["entry"]["clb"], db_clb, "clb info")
            if param["entry"]["polairs"]:
                polairs_info = cluster["clusterentry_set"]["polaris"][0]
                db_polairs = {
                    "name": polairs_info["polaris_name"],
                    "l5": polairs_info["polaris_l5"],
                    "token": polairs_info["polaris_token"],
                }
                self.__check_dict_info(param["entry"]["polairs"], db_polairs, "polaris info")

    def __check_machine(self, input_proxy_list, input_seg_dict, db_proxy_list, db_seg_dict):
        if len(input_proxy_list) != len(db_proxy_list):
            raise Exception("proxy num is diff")
        input_proxy_list.sort()
        db_proxy_list.sort()
        for index, proxy_ins in enumerate(input_proxy_list):
            if db_proxy_list[index] != proxy_ins:
                raise Exception("{} is not in db".format(proxy_ins))
        for seg, ins in input_seg_dict.items():
            if not db_seg_dict.get(seg):
                raise Exception("seg[{}] is not exist in db info]".format(seg))
            if ins["master"] != db_seg_dict[seg]["master"]:
                raise Exception(
                    "seg[{}] master is diff. input[{}],db[{}]".format(seg, ins["master"], db_seg_dict[seg]["master"])
                )
            if ins["slave"] != db_seg_dict[seg]["slave"]:
                raise Exception(
                    "seg[{}] slave is diff. input[{}],db[{}]".format(seg, ins["slave"], db_seg_dict[seg]["slave"])
                )

    def __check_dict_info(self, input_dict: dict, db_dict: dict, notice):
        for k, v in input_dict.items():
            if not db_dict.get(k):
                raise Exception("seg[{}] is not exist in db info]".format(k))
            if v != db_dict[k]:
                raise Exception("seg[{}] {}. input[{}],db[{}]".format(k, notice, v, db_dict[k]))

    def redis_cluster_migrate_compair(self):
        """
        实例列表、seg
        主从关系
        proxy列表
        """
        self.__check(self.data)

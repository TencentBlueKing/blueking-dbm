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
from typing import Dict, Optional

from backend.components import DBConfigApi
from backend.components.db_name_service.client import NameServiceApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.components.dns.client import DnsApi
from backend.db_meta.models import Cluster, Machine
from backend.flow.consts import DEFAULT_TWEMPROXY_SEG_TOTOL_NUM, ConfigTypeEnum

logger = logging.getLogger("flow")


class RedisClusterMigratePrecheckFlow(object):
    """
    redis集群迁移前置检查
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def __check(self, data: dict):
        for cluster_node in data["clusters"]:
            domain = cluster_node["clusterinfo"]["immute_domain"]
            db_version = cluster_node["clusterinfo"]["db_version"]

            proxy_ips = [proxy["ip"] for proxy in cluster_node["proxies"]]
            proxy_ports = [proxy["port"] for proxy in cluster_node["proxies"]]
            if len(set(proxy_ports)) != 1:
                raise Exception("have more diff port {}".format(set(proxy_ports)))
            all_ins = []
            master_ips = []
            slave_ips = []
            all_seg = []
            for backend in cluster_node["backends"]:
                all_seg.append(backend["shard"])
                mip = backend["nodes"]["master"]["ip"]
                sip = backend["nodes"]["slave"]["ip"]
                all_ins.append("{}:{}".format(mip, backend["nodes"]["master"]["port"]))
                all_ins.append("{}:{}".format(sip, backend["nodes"]["slave"]["port"]))
                master_ips.append(mip)
                slave_ips.append(sip)
            # 去重
            master_ips = list(set(master_ips))
            slave_ips = list(set(slave_ips))
            all_ips = master_ips + slave_ips + proxy_ips
            self.__check_meta(all_ips, domain)
            self.__check_params(all_ins, all_seg)

            dbconfig = {
                "bk_biz_id": str(data["bk_biz_id"]),
                "level_name": LevelName.APP,
                "level_value": str(data["bk_biz_id"]),
                "conf_file": db_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": cluster_node["clusterinfo"]["cluster_type"],
                "format": FormatType.MAP,
            }
            self.__check_other_module(domain, cluster_node["entry"]["clb"], cluster_node["entry"]["polairs"], dbconfig)

    def __check_meta(self, ips: list, domain: str):
        """
        机器有没有被复用
        db_meta_machine: 查机器
        db_meta_cluster: 查域名
        db_meta_proxyinstance: 查proxy实例  有外键，不需要检查
        db_meta_storageinstance: 查redis实例  有外键，不需要检查
        """
        if len(ips) != len(set(ips)):
            raise Exception("ip have repetition")
        d = Cluster.objects.filter(immute_domain=domain).values("immute_domain")
        if len(d) != 0:
            raise Exception("domain cluster [{}] is exist.".format(domain))
        m = Machine.objects.filter(ip__in=ips).values("ip")
        if len(m) != 0:
            raise Exception("[{}] is used.".format(m))

    def __check_other_module(self, domain: str, clb: dict, polairs: dict, dbconfig: dict):
        """
        1、域名系统查域名是否已存在
        2、clb、北极星是否已存在
        3、dbconfig中是否已存在对应的db_version模板
        """
        data = DBConfigApi.query_conf_item(params=dbconfig)
        if len(data["content"]) == 0:
            raise Exception("db_version config is not definition")

        res = DnsApi.get_domain({"domain_name": f"{domain}."})
        if len(res["detail"]) == 0:
            raise Exception("domain_name {} is not exist".format(domain))
        if len(clb) != 0:
            res = NameServiceApi.clb_get_target_private_ips(
                {"region": clb["region"], "loadbalancerid": clb["id"], "listenerid": clb["listener_id"]}
            )
            if len(res) == 0:
                raise Exception("clb {} is not exist".format(clb["listener_id"]))

        if len(polairs) != 0:
            res = NameServiceApi.polaris_describe_targets({"servicename": polairs["name"]})
            if len(res) == 0:
                raise Exception("polairs {} is not exist".format(polairs["name"]))

    def __check_params(self, all_ins: list, all_seg: list):
        """
        1、实例是否有重复
        2、seg是否有重复和全覆盖
        """
        if len(all_ins) != len(set(all_ins)):
            raise Exception("ips have repetition")

        begin_seg_list = []
        end_seg_list = []
        try:
            for seg in all_seg:
                begin_seg_list.append(int(str.split(seg, "-")[0]))
                end_seg_list.append(int(str.split(seg, "-")[1]))

            begin_seg_list.sort()
            end_seg_list.sort()

            seg_num = len(begin_seg_list)
            if begin_seg_list[0] != 0 or end_seg_list[seg_num - 1] != DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1:
                raise Exception("redis set is not cover all [{} or {}]".format(0, DEFAULT_TWEMPROXY_SEG_TOTOL_NUM - 1))
            for index in (1, seg_num - 1):
                if begin_seg_list[index] != end_seg_list[index - 1] + 1:
                    raise Exception(
                        "redis set is not cover all [{} ~ {}]".format(begin_seg_list[index], end_seg_list[index - 1])
                    )

        except ImportError as exc:
            raise exc

    def redis_cluster_migrate_precheck_flow(self):
        """
        集群迁移前置检查
        """
        self.__check(self.data)

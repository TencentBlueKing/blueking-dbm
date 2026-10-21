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
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBPrivManagerApi, DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import PrivRole
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.spider.spider_db_function import parse_servers_by_endpoint

SELECT_SERVERS_SQL = "select Host,Port,Wrapper from mysql.servers"
SCHEMA_COUNT_SQL = (
    "select table_schema, count(0) as cnt from information_schema.tables "
    "where table_schema not in ('mysql','information_schema','performance_schema','sys','test') "
    "group by table_schema"
)


class SpiderDRRetainRoutingService(BaseService):
    """接入层灾难重建（仅重建 master）：把保留的 spider_slave / 运维节点重新纳入新中控管理。

    保留节点上已有业务表结构，因此只做「仅路由登记」（create node 不带 with database），
    并先更新保留节点上的接入层内置账号密码（新中控在安装段生成了新的 tdbctl 密码）。
    幂等：已存在且一致的条目跳过，冲突报错；最后 TDBCTL FLUSH ROUTING 并核对。
    """

    def _rpc(self, address: str, bk_cloud_id: int, cmds: List[str], log_desc: str = "", secret: str = "") -> list:
        """执行 DRS 命令。含凭证的 SQL 必须传 log_desc（仅记录描述，不记录原始命令）和 secret（屏蔽报错回显）。"""
        self.log_info(f"exec cmds on [{address}]:[{log_desc or cmds}]")
        res = DRSApi.rpc({"addresses": [address], "cmds": cmds, "force": False, "bk_cloud_id": bk_cloud_id})
        if res[0]["error_msg"]:
            error_msg = res[0]["error_msg"].replace(secret, "xxx") if secret else res[0]["error_msg"]
            raise Exception(f"drs rpc failed: {error_msg}")
        return res[0]["cmd_results"]

    def _grant_account(self, kwargs: dict, cluster: Cluster, node: dict, ctl_ip: str) -> bool:
        """在保留节点上更新内置账号（允许新中控来源连接）"""
        params = {
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_biz_id": int(kwargs["bk_biz_id"]),
            "operator": kwargs["operator"],
            "user": kwargs["tdbctl_user"],
            "psw": kwargs["tdbctl_pass"],
            "hosts": [ctl_ip],
            "dbname": "%",
            "dml_ddl_priv": "",
            "global_priv": "all privileges",
            "address": f'{node["ip"]}{IP_PORT_DIVIDER}{node["port"]}',
            "role": PrivRole.SPIDER.value,
        }
        try:
            DBPrivManagerApi.add_priv_without_account_rule(params)
            self.log_info(_("在[{}]更新接入层内置账号成功").format(params["address"]))
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("[{}]更新内置账号接口异常，相关信息: {}").format(params["address"], e))
            return False
        return True

    def _check_schema_consistency(self, address: str, bk_cloud_id: int, node: dict, ctl_counts: dict) -> None:
        """业务库表数量与中控粗略比对，不一致仅告警（不阻断，避免误伤）"""
        try:
            results = self._rpc(
                f'{node["ip"]}{IP_PORT_DIVIDER}{node["port"]}', bk_cloud_id, ["set tc_admin=0", SCHEMA_COUNT_SQL]
            )
            node_counts = {row["table_schema"]: int(row["cnt"]) for row in results[1]["table_data"]}
        except Exception as e:  # pylint: disable=broad-except
            self.log_warning(_("校验 {} 表结构失败（忽略）: {}").format(node["ip"], e))
            return
        diff = {db for db in set(ctl_counts) | set(node_counts) if ctl_counts.get(db, 0) != node_counts.get(db, 0)}
        if diff:
            self.log_warning(_("保留节点 {} 与中控的业务库表数量不一致（可能存在表结构漂移）: {}").format(node["ip"], sorted(diff)))

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        address = kwargs["ctl_primary"]
        ctl_ip = address.split(IP_PORT_DIVIDER)[0]
        user, passwd = kwargs["tdbctl_user"], kwargs["tdbctl_pass"]
        nodes: List[dict] = kwargs["retain_nodes"]  # [{"ip","port","wrapper"}]

        # 1) 更新保留节点上的内置账号（新密码 + 允许新中控来源）
        for node in nodes:
            if not self._grant_account(kwargs, cluster, node, ctl_ip):
                return False

        try:
            # 2) 查询当前路由，仅登记缺失条目（不带 with database）
            results = self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=1", SELECT_SERVERS_SQL])
            existing = parse_servers_by_endpoint(results[1]["table_data"])

            creates = []
            for node in nodes:
                key = (node["ip"], int(node["port"]))
                current = existing.get(key)
                if current == node["wrapper"]:
                    continue
                if current is not None:
                    self.log_error(
                        _("路由冲突：{}:{} 已存在 wrapper={}，与期望的 {} 不一致，请人工确认").format(
                            node["ip"], node["port"], current, node["wrapper"]
                        )
                    )
                    return False
                creates.append(
                    "tdbctl create node wrapper '{}' options(user '{}', password '{}', host '{}', port {});".format(
                        node["wrapper"], user, passwd, node["ip"], node["port"]
                    )
                )
            if creates:
                self._rpc(
                    address,
                    cluster.bk_cloud_id,
                    ["set tc_admin=1"] + creates,
                    log_desc=_("tdbctl create node x {}（命令含凭证，不记录原文）").format(len(creates)),
                    secret=passwd,
                )
                self.log_info(_("登记保留节点路由: {}").format(["{}:{}".format(n["ip"], n["port"]) for n in nodes]))

            # 3) 全量下发路由
            self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=1", "TDBCTL FLUSH ROUTING"])

            # 4) 核对中控路由表
            results = self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=1", SELECT_SERVERS_SQL])
            final = parse_servers_by_endpoint(results[1]["table_data"])
            missing = [n for n in nodes if final.get((n["ip"], int(n["port"]))) != n["wrapper"]]
            if missing:
                self.log_error(_("保留节点路由核对失败: {}").format(missing))
                return False
        except Exception as e:  # pylint: disable=broad-except
            self.log_error(_("登记保留节点路由失败: {}").format(e))
            return False

        # 5) 表结构粗略一致性校验（仅告警）
        try:
            results = self._rpc(address, cluster.bk_cloud_id, ["set tc_admin=0", SCHEMA_COUNT_SQL])
            ctl_counts = {row["table_schema"]: int(row["cnt"]) for row in results[1]["table_data"]}
        except Exception as e:  # pylint: disable=broad-except
            self.log_warning(_("查询中控业务表数量失败（跳过一致性校验）: {}").format(e))
            ctl_counts = {}
        if ctl_counts:
            for node in nodes:
                self._check_schema_consistency(address, cluster.bk_cloud_id, node, ctl_counts)

        self.log_info(_("[{}] 保留节点路由登记完成，共 {} 个节点").format(cluster.immute_domain, len(nodes)))
        return True


class SpiderDRRetainRoutingComponent(Component):
    name = __name__
    code = "spider_dr_retain_routing"
    bound_service = SpiderDRRetainRoutingService

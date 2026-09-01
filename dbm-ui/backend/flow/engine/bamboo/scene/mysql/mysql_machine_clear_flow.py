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
from dataclasses import asdict
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.common.reset_os_timezone import (
    OsTimeZoneResetComponent,
    OsTimeZoneResetKwargs,
)
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.utils.mysql.dts.script_template import render_clean_data_dir_script, render_stop_process_script
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class ClearMysqlMachineFlow(object):
    """
    构建清理mysql/proxy/spider机器的流程
    兼容跨云区域的执行
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.data["clear_hosts"] = self.data.pop("hosts")

    def _group_hosts_by_cloud(self) -> Dict[int, List[str]]:
        """按 bk_cloud_id 对 clear_hosts 做分组聚合。

        功能说明 / 怎么做：
            - 遍历 ``self.data["clear_hosts"]``（每项形如 ``{"ip": xxx, "bk_cloud_id": xxx, ...}``），
              以 ``bk_cloud_id`` 为 key 将同云区域的 ip 收敛到同一个列表；
            - 供并行下发 OS 时区重置节点时按云区域拆分并发使用。

        :return: dict，key 为 bk_cloud_id (int)，value 为该云区域下的 ip 列表 (List[str])

        边界 / 异常：
            - ``clear_hosts`` 为空 -> 返回空 dict，调用方需自行判空避免生成空的并行网关；
            - 单个 host 缺失 ``ip`` 或 ``bk_cloud_id`` 字段 -> 直接抛 KeyError，属于上游数据错误，
              不做静默兼容，快速失败。
        """
        cloud_to_ips: Dict[int, List[str]] = defaultdict(list)
        for host in self.data["clear_hosts"]:
            cloud_to_ips[host["bk_cloud_id"]].append(host["ip"])
        return dict(cloud_to_ips)

    def _dts_clear_groups(self) -> List[tuple]:
        """按 deploy_path 分组清机目标。单路径时返回一份；多路径来自 dts_deploy_path_by_host。"""
        hosts = self.data.get("clear_hosts") or []
        path_by_host = self.data.get("dts_deploy_path_by_host") or {}
        if not path_by_host:
            deploy_path = self.data.get("dts_deploy_path")
            return [(deploy_path, hosts)] if deploy_path else []

        grouped: Dict[str, List] = defaultdict(list)
        for host in hosts:
            hid = host.get("bk_host_id")
            path = path_by_host.get(str(hid)) or path_by_host.get(hid) or self.data.get("dts_deploy_path")
            if not path:
                raise ValueError(_("DTS 清机缺少 dts_deploy_path，拒绝回退到 MySQL 通用清机脚本"))
            grouped[path].append(host)
        return list(grouped.items())

    def run_flow(self):
        """
        定义清理机器的执行流程
        执行逻辑：
        1: 清理和机器相关的dbm元数据
        2: 清理机器
        3: 按 bk_cloud_id 并行重置各云区域机器的 OS 时区
        """
        # 定义主流程
        main_pipeline = Builder(root_id=self.root_id, data=self.data)

        is_mysql_dts = self.data.get("cluster_type") == ClusterType.MySQLDTS.value
        if not is_mysql_dts:
            main_pipeline.add_act(
                act_name=_("清理机器cmdb元数据"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(DBMetaOPKwargs(db_meta_class_func=MySQLDBMeta.clear_machines.__name__)),
            )

        clear_kwargs = {"exec_ips": self.data["clear_hosts"]}
        if is_mysql_dts:
            path_groups = self._dts_clear_groups()
            if len(path_groups) > 1:
                clear_acts = []
                for deploy_path, hosts in path_groups:
                    clear_acts.append(
                        {
                            "act_name": _("清理机器({})").format(deploy_path),
                            "act_component_code": ClearMachineScriptComponent.code,
                            "kwargs": {
                                "exec_ips": hosts,
                                "clear_machine_script": "\n".join(
                                    [
                                        render_stop_process_script(deploy_path),
                                        render_clean_data_dir_script(deploy_path),
                                    ]
                                ),
                            },
                        }
                    )
                main_pipeline.add_parallel_acts(acts_list=clear_acts)
            else:
                deploy_path = path_groups[0][0] if path_groups else self.data.get("dts_deploy_path")
                if not deploy_path:
                    raise ValueError(_("DTS 清机缺少 dts_deploy_path，拒绝回退到 MySQL 通用清机脚本"))
                clear_kwargs["clear_machine_script"] = "\n".join(
                    [render_stop_process_script(deploy_path), render_clean_data_dir_script(deploy_path)]
                )
                main_pipeline.add_act(
                    act_name=_("清理机器"),
                    act_component_code=ClearMachineScriptComponent.code,
                    kwargs=clear_kwargs,
                )
        else:
            main_pipeline.add_act(
                act_name=_("清理机器"),
                act_component_code=ClearMachineScriptComponent.code,
                kwargs=clear_kwargs,
            )

        # 按 bk_cloud_id 拆分：每个云区域生成一个独立 act，最终通过并行网关一次性下发
        # 目标时区值由组件侧 OsTimeZoneReset._resolve_time_zone 从环境变量
        # ENABLE_DB_MACHINE_TIMEZONE_RESET 读取；env 为空时组件基类 _execute 会走空值短路
        # （不下发 Job、直接短路成功），因此本 flow 不做上游预筛，保持"编排"与"值判断"职责分离
        cloud_to_ips: Dict[int, List[str]] = self._group_hosts_by_cloud()
        if cloud_to_ips:
            timezone_acts: List[Dict] = [
                {
                    "act_name": _("主机时区重置调整(bk_cloud_id={})").format(bk_cloud_id),
                    "act_component_code": OsTimeZoneResetComponent.code,
                    "kwargs": asdict(
                        OsTimeZoneResetKwargs(
                            bk_cloud_id=bk_cloud_id,
                            exec_ip=exec_ips,
                        )
                    ),
                }
                for bk_cloud_id, exec_ips in cloud_to_ips.items()
            ]
            main_pipeline.add_parallel_acts(acts_list=timezone_acts)

        main_pipeline.run_pipeline()

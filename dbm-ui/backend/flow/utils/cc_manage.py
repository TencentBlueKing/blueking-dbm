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

import logging
from typing import Dict, List

from django.db import transaction

from backend import env
from backend.components import CCApi
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterTypeMachineTypeDefine
from backend.db_meta.models import AppMonitorTopo, Cluster, ClusterMonitorTopo, StorageInstance
from backend.db_meta.models.cluster_monitor import INSTANCE_MONITOR_PLUGINS, SET_NAME_TEMPLATE
from backend.db_services.ipchooser.constants import IDLE_HOST_MODULE
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.exceptions import ApiError

logger = logging.getLogger("flow")


class CcManage(object):
    """
    涉及到 bk-cmdb 的操作，都收敛到这个类中
    在这里通过 hosting_biz_id 来决定真实操作 cmdb 的业务
    """

    def __init__(self, bk_biz_id: int):
        # 主机在 cmdb 上实际托管的业务
        self.hosting_biz_id = SystemSettings.get_exact_hosting_biz(bk_biz_id)

    @classmethod
    def get_or_create_set_with_name(cls, bk_biz_id: int, bk_set_name: str) -> int:
        """
        根据名称获取拓扑中的集群id
        @param bk_biz_id: 业务ID
        @param bk_set_name: 集群名
        """
        res = CCApi.search_set(
            params={
                "bk_biz_id": bk_biz_id,
                "fields": ["bk_set_name", "bk_set_id"],
                "condition": {"bk_set_name": bk_set_name},
            },
            use_admin=True,
        )

        if res["count"] > 0:
            return res["info"][0]["bk_set_id"]

        res = CCApi.create_set(
            params={
                "bk_biz_id": bk_biz_id,
                "data": {
                    "bk_parent_id": bk_biz_id,
                    "bk_set_name": bk_set_name,
                },
            },
            use_admin=True,
        )
        return res["bk_set_id"]

    @classmethod
    def get_or_create_module_with_name(cls, bk_biz_id: int, bk_set_id: int, bk_module_name: str) -> int:
        """
        根据名称获取模块id(不同组件属于到不同的模块)
        @param bk_biz_id: 业务ID
        @param bk_set_id: 集群ID
        @param bk_module_name: 模块名字
        """
        res = CCApi.search_module(
            {
                "bk_biz_id": bk_biz_id,
                "bk_set_id": bk_set_id,
                "condition": {"bk_module_name": bk_module_name},
            },
            use_admin=True,
        )

        if res["count"] > 0:
            return res["info"][0]["bk_module_id"]

        res = CCApi.create_module(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_set_id": bk_set_id,
                "data": {"bk_parent_id": bk_set_id, "bk_module_name": bk_module_name},
            },
            use_admin=True,
        )
        return res["bk_module_id"]

    def get_or_create_set_module(
        self,
        db_type: str,
        cluster_type: str,
        bk_module_name: str,
        cluster_id: int = 0,
        instance_id: int = 0,
        creator: str = "",
    ):
        """创建监控拓扑相关模块"""

        machine_topo = {}
        for machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
            monitor_plugin = INSTANCE_MONITOR_PLUGINS[db_type][machine_type]
            try:
                app_monitor_topo = AppMonitorTopo.objects.get(
                    bk_biz_id=self.hosting_biz_id, db_type=db_type, machine_type=machine_type
                )
            except AppMonitorTopo.DoesNotExist:
                # 集群拓扑不存在则创建
                bk_set_name = SET_NAME_TEMPLATE.format(db_type=db_type, monitor_plugin_name=monitor_plugin["name"])
                res = CCApi.search_set({"bk_biz_id": self.hosting_biz_id, "condition": {"bk_set_name": bk_set_name}})
                if res["count"]:
                    bk_set = res["info"][0]
                else:
                    bk_set = CCApi.create_set(
                        {
                            "bk_biz_id": self.hosting_biz_id,
                            "data": {"bk_parent_id": self.hosting_biz_id, "bk_set_name": bk_set_name},
                        },
                        use_admin=True,
                    )
                app_monitor_topo, created = AppMonitorTopo.objects.update_or_create(
                    defaults={"monitor_plugin_id": monitor_plugin["plugin_id"]},
                    bk_biz_id=self.hosting_biz_id,
                    machine_type=machine_type,
                    db_type=db_type,
                    monitor_plugin=monitor_plugin["name"],
                    bk_set_id=bk_set["bk_set_id"],
                    bk_set_name=bk_set["bk_set_name"],
                )

            bk_set_id = app_monitor_topo.bk_set_id

            # cmdb get_or_create_module
            res = CCApi.search_module(
                {
                    "bk_biz_id": self.hosting_biz_id,
                    "bk_set_id": bk_set_id,
                    "condition": {"bk_module_name": bk_module_name},
                },
                use_admin=True,
            )

            if res["count"]:
                bk_module = res["info"][0]
            else:
                bk_module = CCApi.create_module(
                    {
                        "bk_biz_id": self.hosting_biz_id,
                        "bk_set_id": bk_set_id,
                        "data": {"bk_parent_id": bk_set_id, "bk_module_name": bk_module_name},
                    },
                    use_admin=True,
                )

            # 保留一份集群监控拓扑数据
            topo, created = ClusterMonitorTopo.objects.get_or_create(
                defaults={"creator": creator},
                machine_type=machine_type,
                bk_biz_id=self.hosting_biz_id,
                cluster_id=cluster_id,
                instance_id=instance_id,
                bk_set_id=bk_set_id,
                bk_module_id=bk_module["bk_module_id"],
            )
            machine_topo[machine_type] = topo.bk_module_id

        return machine_topo

    def get_biz_internal_module(self, bk_biz_id: int):
        """获取业务下的内置模块"""
        biz_internal_module = ResourceQueryHelper.get_biz_internal_module(bk_biz_id)
        module_type__module = {module["default"]: module for module in biz_internal_module["module"]}
        return module_type__module

    def transfer_host_to_idlemodule(
        self, bk_biz_id: int, bk_host_ids: List[int], biz_idle_module: int = None, host_topo: List[Dict] = None
    ):
        """将主机转移到当前业务的空闲模块"""

        # 获取业务的空闲模块和主机拓扑信息
        biz_idle_module = biz_idle_module or self.get_biz_internal_module(bk_biz_id)[IDLE_HOST_MODULE]["bk_module_id"]
        if not host_topo:
            host_topo = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids})

        host__idle_module = {host["bk_host_id"]: host["bk_module_id"] for host in host_topo}
        transfer_host_ids: List[int] = [
            host_id for host_id in bk_host_ids if host__idle_module[host_id] != biz_idle_module
        ]
        if transfer_host_ids:
            resp = CCApi.transfer_host_to_idlemodule(
                {"bk_biz_id": bk_biz_id, "bk_host_id": transfer_host_ids}, raw=True
            )
            if resp.get("result"):
                return
            # 针对主机已经转移过的场景，直接忽略即可
            if resp.get("bk_error_code") == CCApi.ErrorCode.HOST_NOT_BELONG_BIZ:
                logger.warning(f"transfer_host_to_idlemodule, resp:{resp}")
            else:
                raise ApiError(f"transfer_host_to_idlemodule error, resp:{resp}")

    def transfer_host_module(self, bk_host_ids: list, target_module_ids: list):
        """
        跨业务转移主机，需要先做中转处理
        循环判断处理，逻辑保证幂等操作
        考虑这几种情况：
        1. 业务空闲机 -> 业务模块
        2. 业务空闲机 -> DBA 业务模块
        3. DBA 业务空闲机 -> 业务模块
        4. DBA 业务空闲机 -> DBA 业务模块
        5. DBA 业务资源池 -> DBA 业务空闲机 -> 业务模块/DBA 业务模块
        """
        if not bk_host_ids:
            # 有些角色允许为空，所以要忽略
            return

        # 查询当前bk_hosts_ids的业务对应关系
        logger.info(f"transfer_host_module, bk_host_ids:{bk_host_ids}")
        hosts = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids})

        # 主机当前业务跟目标业务不一致，需转移业务的主机
        need_across_biz_host_ids = []
        src_bk_biz_id = None
        for host in hosts:
            host_biz_id = host["bk_biz_id"]
            if host_biz_id != self.hosting_biz_id:
                src_bk_biz_id = host_biz_id
                need_across_biz_host_ids.append(host["bk_host_id"])

        # 业务id -> 业务空闲机模块映射
        dst_biz_internal_module = CCApi.get_biz_internal_module({"bk_biz_id": self.hosting_biz_id}, use_admin=True)
        free_bk_module_id = None
        # 获取dba空闲机模块的 bk_module_id
        for module in dst_biz_internal_module["module"]:
            if module["default"] == IDLE_HOST_MODULE:
                free_bk_module_id = module["bk_module_id"]

        # 将待跨业务转移主机先转移到当前业务的空闲机
        if need_across_biz_host_ids:
            self.transfer_host_to_idlemodule(
                bk_biz_id=src_bk_biz_id, bk_host_ids=need_across_biz_host_ids, host_topo=hosts
            )
            resp = CCApi.transfer_host_across_biz(
                {
                    "src_bk_biz_id": src_bk_biz_id,
                    "dst_bk_biz_id": self.hosting_biz_id,
                    "bk_host_id": need_across_biz_host_ids,
                    "bk_module_id": free_bk_module_id,
                },
                use_admin=True,
                raw=True,
            )
            if resp.get("result"):
                return
            # 针对主机已经转移过的场景，直接忽略即可
            if resp.get("bk_error_code") == CCApi.ErrorCode.HOST_NOT_BELONG_MODULE:
                logger.warning(f"transfer_host_across_biz, resp:{resp}")
            else:
                raise ApiError(f"transfer_host_across_biz error, resp:{resp}")

        # 主机转移到对应的模块下，机器可能对应多个集群，所有主机转移到多个模块下是合理的
        CCApi.transfer_host_module(
            {
                "bk_biz_id": self.hosting_biz_id,
                "bk_host_id": bk_host_ids,
                "bk_module_id": target_module_ids,
                "is_increment": True,
            },
            use_admin=True,
        )

    def recycle_host(self, bk_host_ids: list):
        """
        转移到待回收模块
        转移主机后会自动删除服务实例，无需额外操作
        """
        CCApi.transfer_host_to_recyclemodule({"bk_biz_id": self.hosting_biz_id, "bk_host_id": bk_host_ids})

    def add_service_instance(
        self,
        bk_module_id: int,
        bk_host_id: int,
        listen_ip: str,
        listen_port: int,
        func_name: str,
        bk_process_name: str,
        labels_dict: dict = None,
    ) -> int:
        """
        定义添加bk-cc的服务实例的公共方法
        @param: bk_module_id: 模块idx
        @param: bk_host_id:   机器id
        @param: listen_ip:    进程监听ip
        @param: listen_port:  进程监听端口（监控依赖）
        @param: func_name:    程序的二进制名称 比如zookeeper的二进制名称是java，则填java（监控依赖）
        @param: bk_process_name:    对外显示的服务名 比如程序的二进制名称为java的服务zookeeper，则填zookeeper
        @param: labels_dict:  待加入的标签字典
        """
        # 检查主机的服务实例，若已存在，则不新建
        service_instances = CCApi.list_service_instance_detail(
            {"bk_biz_id": self.hosting_biz_id, "bk_host_list": [bk_host_id], "page": {"start": 0, "limit": 200}}
        )["info"]
        for ins in service_instances:
            for process in ins.get("process_instances") or []:
                if all(
                    [
                        process["process"]["bk_func_name"] == func_name,
                        process["process"]["bk_process_name"] == bk_process_name,
                        process["process"]["bind_info"][0]["ip"] == listen_ip,
                        process["process"]["bind_info"][0]["port"] == str(listen_port),
                    ]
                ):
                    return ins["id"]

        # 添加服务实例信息，目前只操作一个，所以返回也是只有一个元素
        bk_instance_ids = list(
            CCApi.create_service_instance(
                {
                    "bk_biz_id": self.hosting_biz_id,
                    "bk_module_id": bk_module_id,
                    "instances": [
                        {
                            "bk_host_id": bk_host_id,
                            "processes": [
                                {
                                    "process_template_id": 0,
                                    "process_info": {
                                        "bk_func_name": func_name,
                                        "bk_process_name": bk_process_name,
                                        "bind_info": [
                                            {
                                                "enable": True,
                                                "ip": listen_ip,
                                                "port": str(listen_port),
                                                "protocol": "1",
                                                # "type": func_type,
                                            }
                                        ],
                                    },
                                }
                            ],
                        }
                    ],
                }
            )
        )
        self.add_label_for_service_instance(bk_instance_ids, labels_dict)
        return bk_instance_ids[0]

    def add_label_for_service_instance(self, bk_instance_ids: list, labels_dict: dict):

        # 添加集群信息标签
        if labels_dict:
            CCApi.add_label_for_service_instance(
                {
                    "bk_biz_id": self.hosting_biz_id,
                    "instance_ids": bk_instance_ids,
                    "labels": labels_dict,
                }
            )

    def delete_service_instance(self, bk_instance_ids: List[int]):
        # 这里因为id不存在会导致接口异常退出，这里暂时接收所有错误，不让它直接退出
        try:
            CCApi.delete_service_instance(
                {
                    "bk_biz_id": self.hosting_biz_id,
                    "service_instance_ids": bk_instance_ids,
                }
            )
        except Exception as error:
            logger.warning(error)

    def delete_cc_module(self, db_type: str, cluster_type: str, cluster_id: int = 0, instance_id: int = 0):
        """
        封装方法：现在bkcc的模块是跟cluster_id、db_type 的结合对应
        根据这些信息删除对应模块, 使用场景是回收集群
        """

        for machine_type in ClusterTypeMachineTypeDefine[cluster_type]:
            bk_set_id = AppMonitorTopo.objects.get(
                bk_biz_id=self.hosting_biz_id, db_type=db_type, machine_type=machine_type
            ).bk_set_id

            bk_module_obj = ClusterMonitorTopo.objects.get(
                machine_type=machine_type,
                bk_biz_id=self.hosting_biz_id,
                cluster_id=cluster_id,
                instance_id=instance_id,
                bk_set_id=bk_set_id,
            )
            # 检查模块下是否还有机器

            CCApi.delete_module(
                {
                    "bk_biz_id": bk_module_obj.bk_biz_id,
                    "bk_set_id": bk_module_obj.bk_set_id,
                    "bk_module_id": bk_module_obj.bk_module_id,
                }
            )
            bk_module_obj.delete(keep_parents=True)

    @transaction.atomic
    def delete_cluster_modules(self, db_type, cluster: Cluster):
        """
        @param db_type: db组件类型
        @param cluster： 集群对象
        """
        self.delete_cc_module(db_type, cluster.cluster_type, cluster_id=cluster.id)

    @transaction.atomic
    def delete_instance_modules(self, db_type: str, ins: StorageInstance, cluster_type: str):
        """
        @param db_type: db组件类型
        @param ins： 待删除模块所关联的ins_id
        @param cluster_type： 集群类型
        """
        self.delete_cc_module(db_type, cluster_type, instance_id=ins.id)

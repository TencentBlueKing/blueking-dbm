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
import copy
import logging

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService

logger = logging.getLogger("flow")


class MySQLClearMachineService(ExecuteDBActuatorScriptService):
    """
    定义清理mysql机器的活动节点，判断机器ip在db-meta是否还有记录，如果没有，则执行以下两个行为：
    1：清理机器的crontab配置（root用户下执行，幂等动作）
    2：....
    """

    def _execute(self, data, parent_data) -> bool:
        """
        清理crontab
        """
        kwargs = data.get_one_of_inputs("kwargs")

        if isinstance(kwargs["exec_ip"], str):
            exec_ips = [kwargs["exec_ip"]]
        else:
            exec_ips = kwargs["exec_ip"]

        # 检测机器列表是否还有实例注册
        target_ip_list = copy.deepcopy(exec_ips)
        for ip in exec_ips:
            if Machine.objects.filter(ip=ip, bk_cloud_id=kwargs["bk_cloud_id"]).exists():
                self.log_info(_("机器还在系统中注册，暂不用清理[{}]").format(ip))
                target_ip_list.remove(ip)
                continue
        if not target_ip_list:
            # 表示没有机器可以清理回收
            self.log_info(_("本次操作没有机器可以清理，提前结束活动节点"))
            data.outputs.ext_result = True
            return True

        data.get_one_of_inputs("kwargs")["exec_ip"] = target_ip_list
        return super()._execute(data, parent_data)


class MySQLClearMachineComponent(Component):
    name = __name__
    code = "mysql_clear_machine"
    bound_service = MySQLClearMachineService


class SpiderRemoteClearMachineService(ExecuteDBActuatorScriptService):
    def _execute(self, data, parent_data) -> bool:
        """
        清理tendbcluster接入层和存储层的监控备份等
        tendbcluster机器是集群独占, 所以不需要检查是不是会有空闲实例
        可以直接清理
        """
        kwargs = data.get_one_of_inputs("kwargs")

        if isinstance(kwargs["exec_ip"], str):
            exec_ips = [kwargs["exec_ip"]]
        else:
            exec_ips = kwargs["exec_ip"]

        target_ip_list = copy.deepcopy(exec_ips)

        has_wrong_storage = StorageInstance.objects.filter(machine__ip__in=exec_ips).exclude(
            cluster_type=ClusterType.TenDBCluster
        )
        has_wrong_proxy = ProxyInstance.objects.filter(machine__ip__in=exec_ips).exclude(
            cluster_type=ClusterType.TenDBCluster
        )

        if has_wrong_storage.exists() or has_wrong_proxy.exists():
            self.log_info(
                _(
                    "输入了不是 tendbcluster 的 ip: {} {}".format(
                        list(has_wrong_proxy.values_list("machine__ip", flat=True)),
                        list(has_wrong_storage.values_list("machine__ip", flat=True)),
                    )
                )
            )
            return False

        data.get_one_of_inputs("kwargs")["exec_ip"] = target_ip_list
        return super()._execute(data, parent_data)


class SpiderRemoteClearMachineComponent(Component):
    name = __name__
    code = "spider_remote_clear_machine"
    bound_service = SpiderRemoteClearMachineService

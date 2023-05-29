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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

import backend.flow.utils.hdfs.hdfs_context_dataclass as flow_context
from backend.flow.consts import HdfsRoleEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService


class UpdateHdfsResourceService(BaseService):
    """
    定义HDFS集群域名管理的活动节点,目前只支持添加域名、删除域名
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        trans_data.new_ip = kwargs["new_ip"]
        trans_data.old_ip = kwargs["old_ip"]
        if kwargs["role"] == HdfsRoleEnum.NameNode:
            # 将trans_data NameNode 更新 为新的IP，渲染配置时需要用到
            if trans_data.old_ip == trans_data.cur_nn1_ip:
                trans_data.cur_nn1_ip = trans_data.new_ip
                nn1_host = trans_data.cur_all_ip_hosts.pop(trans_data.old_ip)
                trans_data.cur_all_ip_hosts[trans_data.new_ip] = nn1_host
            else:
                trans_data.cur_nn2_ip = trans_data.new_ip
                nn2_host = trans_data.cur_all_ip_hosts.pop(trans_data.old_ip)
                trans_data.cur_all_ip_hosts[trans_data.new_ip] = nn2_host
        elif kwargs["role"] == HdfsRoleEnum.JournalNode:
            for i in range(len(trans_data.cur_jn_ips)):
                if trans_data.cur_jn_ips[i] == trans_data.old_ip:
                    trans_data.cur_jn_ips[i] = trans_data.new_ip
                    break
        elif kwargs["role"] == HdfsRoleEnum.ZooKeeper:
            # 默认替换ZK操作时JN已全部替换完
            trans_data.cur_zk_ips = trans_data.cur_jn_ips

        # 当前IP
        all_ip_set = {trans_data.cur_nn1_ip, trans_data.cur_nn2_ip}
        all_ip_set.update(trans_data.cur_zk_ips)
        all_ip_set.update(trans_data.cur_dn_ips)
        trans_data.cur_all_ips = list(all_ip_set)

        # 更新主备节点状态
        if trans_data.cluster_active_info:
            trans_data.cur_active_nn_ip = trans_data.cluster_active_info["active"]
            trans_data.cur_standby_nn_ip = trans_data.cluster_active_info["standby"]

        self.log_info(_("更新机器资源成功成功。 {}").format(trans_data))
        data.outputs["trans_data"] = trans_data
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class UpdateHdfsResourceComponent(Component):
    name = __name__
    code = "update_hdfs_resource"
    bound_service = UpdateHdfsResourceService

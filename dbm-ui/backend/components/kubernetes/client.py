# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import KUBERNETES_APIGW_DOMAIN


class _KubernetesApi(BaseApi):
    MODULE = _("k8s 服务")
    BASE = KUBERNETES_APIGW_DOMAIN

    def __init__(self):
        self.cluster_detail = self.generate_data_api(
            method="GET",
            url="/v4/dbs/metadata/cluster/{cluster_id}/",
            description=_("获取集群详情"),
        )
        self.bcs_regions = self.generate_data_api(
            method="GET",
            url="/v4/dbs/metadata/k8s_cluster_config/regions",
            description=_("获取BCS集群信息"),
        )
        self.addon_versions = self.generate_data_api(
            method="GET",
            url="/v4/dbs/metadata/addon/versions",
            description=_("获取存储版本信息"),
        )
        self.addon_spec_plan = self.generate_data_api(
            method="GET",
            url="/v4/dbs/metadata/addon_spec_plan",
            description=_("查询集群部署套餐"),
        )
        self.component_pods = self.generate_data_api(
            method="GET",
            url="/v4/dbs/component/pods",
            description=_("获取组件实例列表"),
        )
        self.pod_detail = self.generate_data_api(
            method="GET",
            url="/v4/dbs/k8s_cluster/pod",
            description=_("获取组件实例详情"),
        )
        self.cluster_describe = self.generate_data_api(
            method="POST",
            url="/v4/dbs/cluster/describe",
            description=_("获取集群信息"),
        )
        self.cluster_operation_log = self.generate_data_api(
            method="POST",
            url="/v4/dbs/metadata/cluster_operation_log",
            description=_("获取集群操作日志"),
        )
        self.restart_component = self.generate_data_api(
            method="POST",
            url="/v4/dbs/opsRequest/restart",
            description=_("重启组件"),
        )
        self.hscaling_component = self.generate_data_api(
            method="POST",
            url="/v4/dbs/opsRequest/hscaling",
            description=_("组件水平扩缩容"),
        )
        self.vscaling_component = self.generate_data_api(
            method="POST",
            url="/v4/dbs/opsRequest/vscaling",
            description=_("组件垂直扩容--升降配"),
        )
        self.vexpansion_component = self.generate_data_api(
            method="POST",
            url="/v4/dbs/opsRequest/vexpansion",
            description=_("组件磁盘扩容"),
        )
        self.delete_component = self.generate_data_api(
            method="POST",
            url="/v4/dbs/cluster/delete",
            description=_("组件实例删除"),
        )
        self.component_config = self.generate_data_api(
            method="GET",
            url="/v4/dbs/dataweb/cluster/config",
            description=_("获取组件配置"),
        )
        self.patch_component_config = self.generate_data_api(
            method="PATCH",
            url="/v4/dbs/dataweb/cluster/config",
            description=_("修改组件配置"),
        )
        self.pod_log = self.generate_data_api(
            method="GET",
            url="/v4/dbs/k8s_cluster/pod/logs",
            description=_("获取组件日志"),
        )
        self.create_cluster = self.generate_data_api(
            method="POST",
            url="/v4/dbs/cluster/create",
            description=_("创建集群"),
        )
        self.apply_clb = self.generate_data_api(
            method="POST",
            url="/v4/dbs/clb/create",
            description=_("创建集群clb"),
        )
        self.get_clb = self.generate_data_api(
            method="POST",
            url="/v4/dbs/clb/get",
            description=_("获取集群clb"),
        )
        self.expose_ports = self.generate_data_api(
            method="POST",
            url="/v4/dbs/opsRequest/expose",
            description=_("暴露端口"),
        )
        self.get_regions = self.generate_data_api(
            method="GET",
            url="/v4/dbs/metadata/k8s_cluster_config/regions?isPublic=true",
            description=_("获取区域列表"),
        )
        self.write_back_cluster_id = self.generate_data_api(
            method="POST",
            url="/v4/dbs/cluster/update_dbm_cluster_id",
            description=_("回写集群ID"),
        )
        self.disable_cluster = self.generate_data_api(
            method="POST", url="/v4/dbs/opsRequest/stop", description=_("禁用集群")
        )


KubernetesApi = _KubernetesApi()

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

from django.utils.translation import ugettext_lazy as _

from ..base import BaseApi
from ..domains import CC_APIGW_DOMAIN


class _CCApi(BaseApi):
    MODULE = _("配置平台")
    BASE = CC_APIGW_DOMAIN

    class ErrorCode:
        HOST_NOT_BELONG_BIZ = 1113002
        HOST_NOT_BELONG_MODULE = 1110056
        CUSTOM_FIELD_ALREADY_EXISTS = 1101107

    def __init__(self):
        self.list_hosts_without_biz = self.generate_data_api(
            method="POST",
            url="list_hosts_without_biz/",
            description=_("没有业务信息的主机查询"),
        )
        self.search_business = self.generate_data_api(
            method="POST",
            url="search_business/",
            description=_("查询业务"),
        )
        self.search_module = self.generate_data_api(
            method="POST",
            url="search_module/",
            description=_("查询模块"),
        )
        self.create_set = self.generate_data_api(
            method="POST",
            url="create_set/",
            description=_("创建集群"),
        )
        self.search_set = self.generate_data_api(
            method="POST",
            url="search_set/",
            description=_("查询集群"),
        )
        self.create_module = self.generate_data_api(
            method="POST",
            url="create_module/",
            description=_("创建模块"),
        )
        self.delete_module = self.generate_data_api(
            method="POST",
            url="delete_module/",
            description=_("删除模块"),
        )
        self.transfer_host_across_biz = self.generate_data_api(
            method="POST",
            url="transfer_host_across_biz/",
            description=_("跨业务转移主机"),
        )
        self.transfer_host_module = self.generate_data_api(
            method="POST",
            url="transfer_host_module/",
            description=_("业务内主机转移模块"),
        )
        self.update_business = self.generate_data_api(method="POST", url="update_business/", description=_("修改业务"))
        self.update_host = self.generate_data_api(method="POST", url="update_host/", description=_("修改主机"))
        self.batch_update_host = self.generate_data_api(
            method="POST", url="batch_update_host/", description=_("批量修改主机")
        )
        self.create_biz_custom_field = self.generate_data_api(
            method="POST",
            url="create_biz_custom_field/",
            description=_("创建自定义字段"),
        )
        self.search_object_attribute = self.generate_data_api(
            method="POST",
            url="search_object_attribute/",
            description=_("获取模型属性"),
        )
        self.create_object_attribute = self.generate_data_api(
            method="POST",
            url="create_object_attribute/",
            description=_("创建模型属性"),
        )
        self.transfer_host_to_idlemodule = self.generate_data_api(
            method="POST",
            url="transfer_host_to_idlemodule/",
            description=_("主机移动到空闲机模块"),
        )
        self.transfer_host_to_recyclemodule = self.generate_data_api(
            method="POST",
            url="transfer_host_to_recyclemodule/",
            description=_("主机移动到待回收模块"),
        )
        self.search_biz_inst_topo = self.generate_data_api(
            method="GET",
            url="search_biz_inst_topo/",
            description=_("查询业务实例拓扑"),
        )
        self.list_biz_hosts = self.generate_data_api(
            method="POST",
            url="list_biz_hosts/",
            description=_("查询业务下的主机"),
        )
        self.list_biz_hosts_topo = self.generate_data_api(
            method="POST",
            url="list_biz_hosts_topo/",
            description=_("查询业务下的主机和拓扑信息"),
        )
        self.get_biz_internal_module = self.generate_data_api(
            method="GET",
            url="get_biz_internal_module/",
            description=_("查询业务的空闲机/故障机/待回收模块"),
        )
        self.find_host_topo_relation = self.generate_data_api(
            method="POST",
            url="find_host_topo_relation/",
            description=_("获取主机与拓扑的关系"),
        )
        self.search_cloud_area = self.generate_data_api(
            method="POST",
            url="search_cloud_area/",  # 默认缓存1h
            cache_time=60 * 60,
            description=_("查询云区域"),
        )
        self.list_host_total_mainline_topo = self.generate_data_api(
            method="POST",
            url="list_host_total_mainline_topo/",
            description=_("查询主机及其对应拓扑"),
        )
        self.create_service_instance = self.generate_data_api(
            method="POST",
            url="create_service_instance/",
            description=_("创建服务实例"),
        )
        self.list_service_instance = self.generate_data_api(
            method="POST",
            url="list_service_instance/",
            description=_("查询服务实例详细信息"),
        )
        self.list_service_instance_by_host = self.generate_data_api(
            method="POST",
            url="list_service_instance_by_host/",
            description=_("直接通过bk_host_id查询服务实例详细信息"),
        )
        self.list_service_instance_detail = self.generate_data_api(
            method="POST",
            url="list_service_instance_detail/",
            description=_("获取服务实例详细信息"),
        )
        self.add_label_for_service_instance = self.generate_data_api(
            method="POST",
            url="add_label_for_service_instance/",
            description=_("服务实例添加标签"),
        )
        self.remove_label_from_service_instance = self.generate_data_api(
            method="POST",
            url="remove_label_from_service_instance/",
            description=_("从服务实例移除标签"),
        )
        self.delete_service_instance = self.generate_data_api(
            method="POST",
            url="delete_service_instance/",
            description=_("删除服务实例"),
        )
        self.create_process_instance = self.generate_data_api(
            method="POST",
            url="create_process_instance/",
            description=_("创建实例进程"),
        )
        self.delete_process_instance = self.generate_data_api(
            method="POST",
            url="delete_process_instance/",
            description=_("删除实例进程"),
        )
        self.list_process_instance = self.generate_data_api(
            method="POST",
            url="list_process_instance/",
            description=_("查询实例进程列表"),
        )
        self.update_process_instance = self.generate_data_api(
            method="POST",
            url="update_process_instance/",
            description=_("更新实例进程"),
        )
        self.delete_module = self.generate_data_api(
            method="POST",
            url="delete_module/",
            description=_("删除模块"),
        )
        self.find_module_with_relation = self.generate_data_api(
            method="POST",
            url="find_module_with_relation/",
            description=_("根据条件查询业务下的模块"),
        )
        self.find_module_host_relation = self.generate_data_api(
            method="POST",
            url="find_module_host_relation/",
            description=_("根据模块ID查询主机和模块的关系"),
        )
        self.find_host_biz_relations = self.generate_data_api(
            method="POST",
            url="find_host_biz_relations/",
            description=_("查询主机业务关系信息"),
        )
        self.search_object_attribute = self.generate_data_api(
            method="POST",
            url="search_object_attribute/",
            description=_("查询对象属性"),
        )


CCApi = _CCApi()

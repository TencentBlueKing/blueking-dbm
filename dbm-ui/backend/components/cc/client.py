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
import itertools

from django.utils.translation import ugettext_lazy as _

from ...utils.batch_request import request_multi_thread
from ..base import BaseApi
from ..domains import CC_APIGW_DOMAIN


class _CCApi(BaseApi):
    MODULE = _("配置平台")
    BASE = CC_APIGW_DOMAIN

    class ErrorCode:
        HOST_NOT_BELONG_BIZ = 1113002
        HOST_NOT_BELONG_MODULE = 1110056
        CUSTOM_FIELD_ALREADY_EXISTS = 1101107
        TASK_ALREADY_EXISTS = 1199087

    def __init__(self):
        self.list_hosts_without_biz = self.generate_data_api(
            method="POST",
            url="/hosts/list_hosts_without_app",
            description=_("没有业务信息的主机查询"),
        )
        self.search_business = self.generate_data_api(
            method="POST", url="/biz/search/bk_supplier_account", description=_("查询业务"), cache_time=900
        )
        self.search_module = self.generate_data_api(
            method="POST",
            url="/module/search/bk_supplier_account/{bk_biz_id}/{bk_set_id}",
            description=_("查询模块"),
        )
        self.create_set = self.generate_data_api(
            method="POST",
            url="/set/{bk_biz_id}",
            description=_("创建集群"),
        )
        self.search_set = self.generate_data_api(
            method="POST",
            url="/set/search/bk_supplier_account/{bk_biz_id}",
            description=_("查询集群"),
        )
        self.create_module = self.generate_data_api(
            method="POST",
            url="/module/{bk_biz_id}/{bk_set_id}/",
            description=_("创建模块"),
        )
        self.delete_module = self.generate_data_api(
            method="DELETE",
            url="/module/{bk_biz_id}/{bk_set_id}/{bk_module_id}",
            description=_("删除模块"),
        )
        self.transfer_host_across_biz = self.generate_data_api(
            method="POST",
            url="/hosts/modules/across/biz",
            description=_("跨业务转移主机"),
        )
        self.transfer_host_module = self.generate_data_api(
            method="POST",
            url="/hosts/modules/",
            description=_("业务内主机转移模块"),
        )
        self.update_business = self.generate_data_api(
            method="PUT", url="/biz/bk_supplier_account/{bk_biz_id}", description=_("修改业务")
        )
        self.update_host = self.generate_data_api(method="PUT", url="/hosts/batch", description=_("修改主机"))
        self.batch_update_host = self.generate_data_api(
            method="PUT", url="/hosts/property/batch", description=_("批量修改主机")
        )
        self.create_biz_custom_field = self.generate_data_api(
            method="POST",
            url="/create/objectattr/biz/{bk_biz_id}",
            description=_("创建自定义字段"),
        )
        self.search_object_attribute = self.generate_data_api(
            method="POST", url="/find/objectattr", description=_("获取模型属性"), cache_time=60
        )
        self.create_object_attribute = self.generate_data_api(
            method="POST",
            url="/create/objectattr",
            description=_("创建模型属性"),
        )
        self.transfer_host_to_idlemodule = self.generate_data_api(
            method="POST",
            url="/hosts/modules/idle",
            description=_("主机移动到空闲机模块"),
        )
        self.transfer_host_to_recyclemodule = self.generate_data_api(
            method="POST",
            url="/hosts/modules/recycle",
            description=_("主机移动到待回收模块"),
        )
        self.search_biz_inst_topo = self.generate_data_api(
            method="POST", url="/find/topoinst/biz/{bk_biz_id}", description=_("查询业务实例拓扑"), cache_time=60
        )
        self.list_biz_hosts = self.generate_data_api(
            method="POST",
            url="/hosts/app/{bk_biz_id}/list_hosts",
            description=_("查询业务下的主机"),
        )
        self.list_biz_hosts_topo = self.generate_data_api(
            method="POST",
            url="/hosts/app/{bk_biz_id}/list_hosts_topo",
            description=_("查询业务下的主机和拓扑信息"),
        )
        self.get_biz_internal_module = self.generate_data_api(
            method="GET",
            url="/topo/internal/bk_supplier_account/{bk_biz_id}",
            description=_("查询业务的空闲机/故障机/待回收模块"),
            cache_time=60 * 60,
        )
        self.find_host_topo_relation = self.generate_data_api(
            method="POST",
            url="/host/topo/relation/read",
            description=_("获取主机与拓扑的关系"),
        )
        self.search_cloud_area = self.generate_data_api(
            method="POST",
            url="/findmany/cloudarea",
            cache_time=60,
            description=_("查询云区域"),
        )
        self.list_host_total_mainline_topo = self.generate_data_api(
            method="POST",
            url="/findmany/hosts/total_mainline_topo/biz/{bk_biz_id}",
            description=_("查询主机及其对应拓扑"),
        )
        self.create_service_instance = self.generate_data_api(
            method="POST",
            url="/create/proc/service_instance",
            description=_("创建服务实例"),
        )
        self.list_service_instance = self.generate_data_api(
            method="POST",
            url="/findmany/proc/service_instance",
            description=_("查询服务实例详细信息"),
        )
        self.list_service_instance_by_host = self.generate_data_api(
            method="POST",
            url="/findmany/proc/service_instance/with_host",
            description=_("直接通过bk_host_id查询服务实例详细信息"),
        )
        self.list_service_instance_detail = self.generate_data_api(
            method="POST",
            url="/findmany/proc/service_instance/details",
            description=_("获取服务实例详细信息"),
        )
        self.add_label_for_service_instance = self.generate_data_api(
            method="POST",
            url="/createmany/proc/service_instance/labels",
            description=_("服务实例添加标签"),
        )
        self.remove_label_from_service_instance = self.generate_data_api(
            method="DELETE",
            url="/deletemany/proc/service_instance/labels",
            description=_("从服务实例移除标签"),
        )
        self.delete_service_instance = self.generate_data_api(
            method="DELETE",
            url="/deletemany/proc/service_instance",
            description=_("删除服务实例"),
        )
        self.create_process_instance = self.generate_data_api(
            method="POST",
            url="/create/proc/process_instance",
            description=_("创建实例进程"),
        )
        self.delete_process_instance = self.generate_data_api(
            method="DELETE",
            url="/delete/proc/process_instance",
            description=_("删除实例进程"),
        )
        self.list_process_instance = self.generate_data_api(
            method="POST",
            url="/findmany/proc/process_instance",
            description=_("查询实例进程列表"),
        )
        self.update_process_instance = self.generate_data_api(
            method="POST",
            url="/update/proc/process_instance",
            description=_("更新实例进程"),
        )
        self.find_module_with_relation = self.generate_data_api(
            method="POST",
            url="/findmany/module/with_relation/biz/{bk_biz_id}",
            description=_("根据条件查询业务下的模块"),
        )
        self.find_module_host_relation = self.generate_data_api(
            method="POST",
            url="/findmany/module_relation/bk_biz_id/{bk_biz_id}",
            description=_("根据模块ID查询主机和模块的关系"),
        )
        self.find_host_biz_relations = self.generate_data_api(
            method="POST",
            url="/hosts/modules/read",
            description=_("查询主机业务关系信息"),
        )
        self.find_module_batch = (
            self.generate_data_api(
                method="POST",
                url="/findmany/module/bk_biz_id/{bk_biz_id}",
                description=_("批量查询某业务的模块详情"),
            ),
        )
        self.check_host_event = self.generate_data_api(
            method="POST",
            url="event/watch/resource/{bk_resource}",
            description=_("查询主机更新事件信息"),
        )

    def batch_find_host_biz_relations(self, params):
        """批量请求主机拓扑关系"""
        host_ids = params.get("bk_host_id")
        if not host_ids:
            return []

        batch = 500
        params_list = [{"params": {"bk_host_id": host_ids[i : i + batch]}} for i in range(0, len(host_ids), batch)]
        data_list = request_multi_thread(self.find_host_biz_relations, params_list, get_data=lambda x: x)
        return list(itertools.chain(*data_list))


CCApi = _CCApi()

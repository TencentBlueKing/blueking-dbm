# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import DBRESOURCE_APIGW_DOMAIN


class _DBResourceApi(BaseApi):
    MODULE = _("资源池 服务")
    BASE = DBRESOURCE_APIGW_DOMAIN

    def __init__(self):
        self.resource_import = self.generate_data_api(
            method="POST",
            url="resource/import",
            description=_("资源导入"),
            default_timeout=60,
            max_retry_times=1,
        )
        self.resource_reimport = self.generate_data_api(
            method="POST",
            url="resource/reimport",
            description=_("资源重导入"),
        )
        self.resource_list = self.generate_data_api(
            method="POST",
            url="resource/list",
            description=_("资源池资源列表"),
        )
        self.resource_list_all = self.generate_data_api(
            method="POST",
            url="resource/list/all",
            description=_("资源池全部资源列表"),
        )
        self.same_svr_owner_ips = self.generate_data_api(
            method="POST",
            url="resource/same_svr_owner/ips",
            description=_("查询同母机 IP"),
        )
        self.resource_apply = self.generate_data_api(
            method="POST",
            url="resource/apply",
            description=_("资源池资源申请"),
            # 调整超时时长，关闭重试
            default_timeout=60,
            max_retry_times=1,
        )
        self.get_mountpoints = self.generate_data_api(
            method="POST",
            url="resource/mountpoints",
            description=_("获取挂载点"),
        )
        self.get_disktypes = self.generate_data_api(
            method="POST",
            url="resource/disktypes",
            description=_("获取磁盘类型"),
        )
        self.get_subzones = self.generate_data_api(
            method="POST",
            url="resource/subzones",
            description=_("根据逻辑城市查询园区"),
        )
        self.resource_pre_apply = self.generate_data_api(
            method="POST",
            url="resource/pre-apply",
            description=_("资源申请预占用"),
        )
        self.resource_confirm = self.generate_data_api(
            method="POST",
            url="resource/confirm/apply",
            description=_("资源申请确认"),
        )
        self.resource_delete = self.generate_data_api(
            method="POST",
            url="resource/delete",
            description=_("资源删除"),
        )
        self.resource_update = self.generate_data_api(
            method="POST",
            url="resource/update",
            description=_("资源更新"),
        )
        self.resource_batch_update = self.generate_data_api(
            method="POST",
            url="resource/batch/update",
            description=_("资源批量更新"),
        )
        self.get_device_class = self.generate_data_api(
            method="POST",
            url="/resource/deviceclass",
            description=_("获取机型List"),
        )
        self.operation_list = self.generate_data_api(
            method="POST",
            url="/resource/operation/list",
            description=_("获取操作记录"),
        )
        self.import_operation_create = self.generate_data_api(
            method="POST",
            url="/resource/operation/create",
            description=_("创建导入操作记录"),
        )
        self.apply_count = self.generate_data_api(
            method="POST",
            url="/resource/spec/sum",
            description=_("预申请获取资源数量"),
        )
        self.resource_group_count = self.generate_data_api(
            method="POST", url="/statistic/groupby/resource_type", description=_("按照组件统计资源数量")
        )
        self.resource_summary = self.generate_data_api(
            method="POST", url="/statistic/summary", description=_("按照条件聚合资源统计")
        )
        self.resource_label_count = self.generate_data_api(
            method="POST", url="/resource/groupby/label/count", description=_("按照标签统计资源数量")
        )
        self.resource_append_labels = self.generate_data_api(
            method="POST",
            url="/resource/append/labels",
            description=_("追加标签"),
        )
        self.water_level = self.generate_data_api(method="POST", url="/statistic/water_level", description=_("资源水位"))
        # resource/param/query
        self.resource_param_query = self.generate_data_api(
            method="POST",
            url="resource/param/query",
            description=_("根据单据ID/任务ID查询资源请求参数"),
        )
        self.resource_osname = self.generate_data_api(
            method="POST", url="resource/list/osname", description=_("获取所有的操作系统名称")
        )
        self.resource_lack_analysis = self.generate_data_api(
            method="POST",
            url="resource/analysis/result",
            description=_("资源申请不足分析"),
        )
        # CVM 主机详情查询接口
        # ---------------------------------------------------------------------
        # POST /resource/cvm/detail
        #
        # 用途：根据内网 IP 列表批量查询云主机（CVM）实例详情。返回的数据来自
        #       云厂商 OpenAPI（如腾讯云 CVM DescribeInstances + DescribeDisks），
        #       常用于：
        #         1. 回填 Machine.storage_device（数据盘 disk_id / 类型 / 大小）
        #         2. 资源池导入前查询机器机型/规格
        #       注意: Machine.cloud_inst_id(ins-xxx) 来自 CMDB 的 bk_cloud_inst_id, 不是本接口返回的 instanceAssetId
        #
        # 请求体：
        #   {"ips": ["127.0.0.1", "127.0.0.2"]}
        #
        # 响应 data 为 dict，key 为内网 IP，value 为该机器详情：
        #   {
        #     "127.0.0.1": {
        #       "cpu": 2,                                # CPU 核数
        #       "memory": 4,                             # 内存 (GB)
        #       "systemDiskDisksize": 100,               # 系统盘大小 (GB)
        #       "instanceType": "SA2.MEDIUM4",           # 云厂商机型
        #       "lanIp": "127.0.0.1",                    # 内网 IP
        #       "datadiskList": [                        # 数据盘列表
        #         {"DiskSize": 50, "DiskType": "CLOUD_PREMIUM", "DiskId": "disk-xxx"}
        #         # DiskType 原生云盘类型取值:
        #         #   CLOUD_PREMIUM 高性能云硬盘 / CLOUD_BSSD 通用型SSD / CLOUD_SSD SSD云硬盘
        #         #   CLOUD_HSSD 增强型SSD / CLOUD_TSSD 极速型SSD
        #       ],
        #       "cloudCampusName": "南京一区",           # 园区名
        #       "instanceAssetId": "TC220518009547"      # 资产 ID(注意: 非云主机实例 ID ins-xxx)
        #     }
        #   }
        self.resource_cvm_detail = self.generate_data_api(
            method="POST",
            url="resource/cvm/detail",
            description=_("查询 CVM 主机详情"),
        )


DBResourceApi = _DBResourceApi()

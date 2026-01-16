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
from datetime import datetime, timedelta

from django.utils.translation import gettext as _

from ...configuration.constants import HCM_DISK_CLASS_MAP, SystemSettingsEnum
from ...configuration.models import SystemSettings
from ...db_meta.models.city_map import BKSubzone
from ...db_services.cmdb.biz import get_hcm_apply_resource_biz, get_resource_biz
from .. import CCApi
from ..base import BaseApi
from ..domains import HCM_APIGW_DOMAIN
from ..exception import DataAPIException


class _HCMApi(BaseApi):
    MODULE = _("HCM海垒 服务")
    BASE = HCM_APIGW_DOMAIN

    def __init__(self):
        self.list_cvm_device = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/config/findmany/config/cvm/device/detail/",
            description=_("获取可用的CVM机型"),
        )
        self.dissolve_check = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/dissolve/hosts/status/check/",
            description=_("查询主机是否为待裁撤阶段"),
        )
        self.uwork_check = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/hosts/uwork_tickets/status/check/",
            description=_("检查主机是否有未完结的uwork单据"),
        )
        self.create_biz_recycle = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/create/recycle/order",
            description=_("创建业务下的资源回收单据"),
        )
        self.create_biz_apply = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/create/apply",
            description=_("创建业务下的资源申请单据"),
        )
        self.get_apply_status = self.generate_data_api(
            method="GET",
            url="/api/v1/task/get_apply_status/{order_id}",
            description=_("资源申请单据状态查询"),
        )
        self.get_apply_device = self.generate_data_api(
            method="POST",
            url="/api/v1/task/get_apply_device",
            description=_("资源申请已交付机器列表查询"),
        )
        self.update_ticket_apply_terminate = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/terminate/apply",
            description=_("终止CVM申领单据"),
        )
        self.update_ticket_apply_start = self.generate_data_api(
            method="POST",
            url="/api/v1/woa/bizs/{bk_biz_id}/task/start/apply",
            description=_("重试CVM申领单据"),
        )

    def check_host_is_dissolved(self, bk_host_ids: list):
        if not HCM_APIGW_DOMAIN or not bk_host_ids:
            return []

        dissolved_hosts = []
        # 查询主机的业务信息，这里查询的主机要求为统一业务(暂不做校验)
        biz = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids[:1]}, use_admin=True)[0]["bk_biz_id"]

        def __check_dissolve(check_host_ids):
            # 查询裁撤主机列表
            resp = self.dissolve_check(params={"bk_biz_id": biz, "bk_host_ids": check_host_ids}, use_admin=True)
            dissolved_hosts.extend([d["bk_host_id"] for d in resp["info"] if d["status"]])

        # hcm 一次校验不能超过100，这里分批次校验，考虑下架大量机器的情况较少，这里直接串行提交
        batch = 90
        for index in range(0, len(bk_host_ids), batch):
            __check_dissolve(bk_host_ids[index : index + batch])

        return dissolved_hosts

    def check_host_has_uwork(self, bk_host_ids: list):
        if not HCM_APIGW_DOMAIN or not bk_host_ids:
            return {}

        has_uwork_hosts_map = {}
        # 查询主机的业务信息，这里查询的主机要求为统一业务(暂不做校验)
        biz = CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids[:1]}, use_admin=True)[0]["bk_biz_id"]

        def __check_uwork(check_host_ids):
            # 查询包含uwork主机列表
            resp = self.uwork_check(params={"bk_biz_id": biz, "bk_host_ids": check_host_ids}, use_admin=True)
            has_uwork_hosts_map.update({d["bk_host_id"]: d for d in resp["details"] if d["has_open_tickets"]})

        # hcm 一次校验不能超过100，这里分批次校验，考虑下架大量机器的情况较少，这里直接串行提交
        batch = 90
        for index in range(0, len(bk_host_ids), batch):
            __check_uwork(bk_host_ids[index : index + batch])

        return has_uwork_hosts_map

    def create_recycle(self, bk_host_ids: list):
        params = {
            # 所有待回收的机器一定在资源池管控业务
            "bk_biz_id": get_resource_biz(),
            "bk_host_ids": bk_host_ids,
            "remark": "dbm auto create",
            # 回收策略固定是：立刻销毁
            "return_plan": {"cvm": "IMMEDIATE", "pm": "IMMEDIATE"},
        }
        resp = self.create_biz_recycle(params=params)
        return resp["info"][0]["order_id"]

    def create_apply(
        self,
        bk_biz_id: str,
        username: str,
        city: str,
        subzone: str,
        os_name: str,
        device_type: str,
        disk: list,
        count: int,
    ):
        """
        HCM资源申请规则：
        1. 申请类型：滚服项目
        2. 主机亲和性：无亲和性
        3. 机型：从申请规的机型列表中取第一个
        4. 磁盘：忽略本地盘，SSD-云硬盘：CLOUD_SSD，普通云硬盘：CLOUD_PREMIUM，无限制：CLOUD_PREMIUM。
           系统盘默认申请CLOUD_SSD 50G。数据盘取规格里硬盘最小值
        5. 计费模式：包年包月，36个月
        6. 继承云实例ID：在弹性资源池cc上找到一个同地域同机型的主机固资编号，如果无法找到则不能申请改类型规格的机器
        """
        bk_biz_id = get_hcm_apply_resource_biz()
        hcm_image_map = SystemSettings.get_setting_value(SystemSettingsEnum.HCM_OS_NAME_IMAGE_MAP, default={})
        hcm_image_map = {key.strip().lower(): value for key, value in hcm_image_map.items()}

        # 查询cc的园区需要拿园区映射关系（HCM可能是虚拟园区，要拿映射的真实园区查询）
        subzone_map = SystemSettings.get_setting_value(SystemSettingsEnum.REPLENISH_SUBZONE_MAP, {})
        subzones = subzone_map.get(subzone) or [subzone]

        # 根据操作系统名称获取镜像ID
        image_id = hcm_image_map.get(os_name.strip().lower())
        if not image_id:
            raise DataAPIException(_("未找到操作系统{}对应的镜像ID").format(os_name))

        # 查询业务下同地域同机型的任意一个机器云区域实例ID
        filters = {
            "condition": "AND",
            "rules": [
                {"field": "bk_svr_device_cls_name", "operator": "equal", "value": device_type},
                {"field": "idc_city_name", "operator": "equal", "value": city},
                {"field": "sub_zone", "operator": "in", "value": subzones},
            ],
        }
        params = {
            "fields": ["bk_cloud_inst_id"],
            "host_property_filter": filters,
            "page": {"start": 0, "limit": 1},
            "bk_biz_id": bk_biz_id,
        }
        host = CCApi.list_biz_hosts(params, use_admin=True)["info"]
        if not host:
            raise DataAPIException(_("未找到同地域同机型的机器"))

        # 查询云可用区和云地域
        try:
            bk_subzone = BKSubzone.objects.get(bk_sub_zone=subzone)
        except BKSubzone.DoesNotExist:
            raise DataAPIException(_("BKSubzone未找到可用区记录: {}").format(subzone))

        # 预期申请时间定位当前时间+3月(HCM规则?)
        expect_apply_time = str((datetime.now() + timedelta(days=91)).strftime("%Y-%m-%d %H:%M:%S"))

        suborder_params = {
            # 资源类型：腾讯云虚拟机
            "resource_type": "QCLOUDCVM",
            "replicas": count,
            "spec": {
                "region": bk_subzone.bk_cloud_region,
                "zone": bk_subzone.bk_cloud_zone,
                # 按机型申请
                "resource_mode": 0,
                "device_type": device_type,
                "image_id": image_id,
                # 操作系统盘默认高性能云盘-50G
                "system_disk": {"disk_type": "CLOUD_PREMIUM", "disk_size": 50},
                "data_disk": [
                    {"disk_type": HCM_DISK_CLASS_MAP[d["disk_type"]], "disk_size": d["disk_size"], "disk_num": 1}
                    for d in disk
                    if d["disk_type"] in HCM_DISK_CLASS_MAP
                ],
                # 计费时长固定为包年包月，36个月
                "charge_type": "PREPAID",
                "charge_months": 36,
                "inherit_instance_id": host[0]["bk_cloud_inst_id"],
            },
        }
        apply_params = {
            "bk_biz_id": bk_biz_id,
            "bk_username": username,
            # 需求类型。1: 常规项目; 2: 春节保障; 3: 机房裁撤; 6: 滚服项目; 7: 小额绿通。补货都走滚服申请
            "require_type": 6,
            "expect_time": expect_apply_time,
            "suborders": [suborder_params],
            "remark": _("DBM资源补货申请"),
        }
        ticket_id = self.create_biz_apply(params=apply_params, use_admin=True)["order_id"]
        return ticket_id


HCMApi = _HCMApi()

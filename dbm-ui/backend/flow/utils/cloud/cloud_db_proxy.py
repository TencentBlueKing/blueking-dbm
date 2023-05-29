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
from dataclasses import asdict
from typing import List

from django.db.transaction import atomic
from django.utils.translation import ugettext as _

from backend.db_proxy.constants import ExtensionServiceStatus, ExtensionType
from backend.db_proxy.models import DBCloudProxy, DBExtension
from backend.flow.consts import CloudServiceModuleName
from backend.flow.utils.cloud.cloud_context_dataclass import (
    CloudDBHADetail,
    CloudDNSDetail,
    CloudDRSDetail,
    CloudNginxDetail,
    CloudRedisDTSDetail,
)
from backend.flow.utils.cloud.cloud_module_operate import CloudModuleHandler

logger = logging.getLogger("flow")


class CloudDBProxy:
    """
    这里记录的是云区域服务操作后入库的proxy信息
    """

    def __init__(self, ticket_data: dict, kwargs: dict, cloud_id: int):
        """
        @param ticket_data: 部署单据数据
        @param kwargs: 当前CloudProxyService中的私有数据
        @param cloud_id: 云区域ID
        """
        self.ticket_data = ticket_data
        self.kwargs = kwargs
        self.bk_cloud_id = cloud_id

    def write(self) -> bool:
        func_name = self.kwargs["proxy_func_name"].lower()
        if hasattr(self, func_name):
            return getattr(self, func_name)()
        else:
            logger.error(_("找不到单据类型需要变更的proxy函数，服务信息入库失败"))
            return False

    def cloud_base_apply(self, host_infos, extension_type, detail_class, transfer_module) -> bool:
        """
        云区域组件服务部署信息通用函数
        @param host_infos: 部署主机信息
        @param extension_type: 部署组件类型
        @param detail_class: 部署主机的额外detail的类
        @param transfer_module: 转移的模块
        """
        extensions: List[DBExtension] = []
        bk_host_ids: List[int] = []
        for host_info in host_infos:
            details = asdict(detail_class(**host_info))
            extensions.append(
                DBExtension(
                    bk_cloud_id=self.bk_cloud_id,
                    extension=extension_type,
                    status=ExtensionServiceStatus.RUNNING.value,
                    details=details,
                )
            )
            bk_host_ids.append(host_info["bk_host_id"])

        with atomic():
            DBExtension.objects.bulk_create(extensions)
            CloudModuleHandler.transfer_hosts_in_cloud_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                bk_host_ids=bk_host_ids,
                bk_module_name=transfer_module,
            )

        return True

    def cloud_base_reduce(self, host_infos, move_module):
        extension_ids = [host["id"] for host in host_infos]
        host_ids = [host["bk_host_id"] for host in host_infos]
        with atomic():
            DBExtension.objects.filter(id__in=extension_ids).delete()
            CloudModuleHandler.remove_host_from_origin_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                bk_host_ids=host_ids,
                bk_module_name=move_module,
            )

        return True

    def cloud_base_replace(self, new_host, old_host, change_module):
        with atomic():
            ext = DBExtension.objects.get(id=old_host["id"])
            ext.update_details(**new_host)
            # 挪模块
            CloudModuleHandler.transfer_hosts_in_cloud_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                bk_host_ids=[new_host["bk_host_id"]],
                bk_module_name=change_module,
            )
            CloudModuleHandler.remove_host_from_origin_module(
                bk_biz_id=self.ticket_data["bk_biz_id"],
                bk_host_ids=[old_host["bk_host_id"]],
                bk_module_name=change_module,
            )

        return True

    def cloud_nginx_apply(self) -> bool:
        """nginx服务部署信息"""
        host = self.kwargs["host_infos"][0]
        with atomic():
            res = self.cloud_base_apply(
                host_infos=self.kwargs["host_infos"],
                extension_type=ExtensionType.NGINX,
                detail_class=CloudNginxDetail,
                transfer_module=CloudServiceModuleName.Nginx,
            )
            DBCloudProxy.objects.create(
                bk_cloud_id=self.bk_cloud_id, internal_address=host["ip"], external_address=host["bk_outer_ip"]
            )
        return res

    def cloud_nginx_reload(self) -> bool:
        """nginx reload服务不需要更新任何元数据"""
        pass

    def cloud_nginx_replace(self) -> bool:
        """
        nginx替换元信息写入：
        - 将新的nginx信息更新到旧nginx信息上
        - 将新的nginx机器挪入模块，并将旧nginx机器挪到待回收
        """
        nginx_host = self.kwargs["host_infos"][0]
        old_nginx_host = self.kwargs["details"]["old_nginx"][0]
        with atomic():
            DBCloudProxy.objects.filter(bk_cloud_id=self.bk_cloud_id).update(
                internal_address=nginx_host["ip"], external_address=nginx_host["bk_outer_ip"]
            )
            self.cloud_base_replace(
                new_host=nginx_host, old_host=old_nginx_host, change_module=CloudServiceModuleName.Nginx
            )

        return True

    def cloud_dns_apply(self) -> bool:
        """dns服务部署信息"""
        res = self.cloud_base_apply(
            host_infos=self.kwargs["host_infos"],
            extension_type=ExtensionType.DNS,
            detail_class=CloudDNSDetail,
            transfer_module=CloudServiceModuleName.DNS,
        )
        return res

    def cloud_dns_reduce(self) -> bool:
        res = self.cloud_base_reduce(host_infos=self.kwargs["host_infos"], move_module=CloudServiceModuleName.DNS)
        return res

    def cloud_dns_replace(self) -> bool:
        res = self.cloud_base_replace(
            new_host=self.kwargs["host_infos"][0],
            old_host=self.kwargs["details"]["old_dns"][0],
            change_module=CloudServiceModuleName.DNS,
        )
        return res

    def cloud_dbha_apply(self) -> bool:
        """dbha服务部署信息"""
        res = self.cloud_base_apply(
            host_infos=self.kwargs["host_infos"],
            detail_class=CloudDBHADetail,
            extension_type=ExtensionType.DBHA,
            transfer_module=CloudServiceModuleName.DBHA,
        )
        return res

    def cloud_dbha_reduce(self) -> bool:
        """dbha服务裁撤信息"""
        res = self.cloud_base_reduce(host_infos=self.kwargs["host_infos"], move_module=CloudServiceModuleName.DBHA)
        return res

    def cloud_dbha_replace(self) -> bool:
        """dbha服务替换信息"""
        if self.kwargs["details"]["old_gm"]:
            old_host = self.kwargs["details"]["old_gm"][0]
        else:
            old_host = self.kwargs["details"]["old_agent"][0]

        res = self.cloud_base_replace(
            new_host=self.kwargs["host_infos"][0],
            old_host=old_host,
            change_module=CloudServiceModuleName.DBHA,
        )

        return res

    def cloud_drs_apply(self) -> bool:
        """drs服务部署信息"""
        res = self.cloud_base_apply(
            host_infos=self.kwargs["host_infos"],
            detail_class=CloudDRSDetail,
            extension_type=ExtensionType.DRS,
            transfer_module=CloudServiceModuleName.DRS,
        )
        return res

    def cloud_drs_reduce(self) -> bool:
        """drs服务裁撤信息"""
        res = self.cloud_base_reduce(host_infos=self.kwargs["host_infos"], move_module=CloudServiceModuleName.DRS)
        return res

    def cloud_drs_replace(self) -> bool:
        """drs服务替换信息"""
        res = self.cloud_base_replace(
            new_host=self.kwargs["host_infos"][0],
            old_host=self.kwargs["details"]["old_drs"][0],
            change_module=CloudServiceModuleName.DRS,
        )
        return res

    def cloud_redis_dts_server_apply(self) -> bool:
        """redis dts服务部署信息"""
        res = self.cloud_base_apply(
            host_infos=self.kwargs["host_infos"],
            extension_type=ExtensionType.REDIS_DTS,
            detail_class=CloudRedisDTSDetail,
            transfer_module=CloudServiceModuleName.RedisDTS,
        )
        return res

    def cloud_redis_dts_server_reduce(self) -> bool:
        res = self.cloud_base_reduce(host_infos=self.kwargs["host_infos"], move_module=CloudServiceModuleName.RedisDTS)
        return res

    def cloud_redis_dts_server_replace(self) -> bool:
        res = self.cloud_base_replace(
            new_host=self.kwargs["host_infos"][0],
            old_host=self.kwargs["details"]["old_redis_dts"][0],
            change_module=CloudServiceModuleName.RedisDTS,
        )
        return res

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

from django.db.transaction import atomic
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components.dns.client import DnsApi
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class TransferClusterMetaToOtherBiz(BaseService):
    """
    转移集群元数据到其他业务
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        target_biz_id = kwargs.get("target_biz_id")
        db_module_id = kwargs.get("db_module_id")
        cluster_domain_list = kwargs.get("cluster_domain_list")
        with atomic():
            Cluster.objects.filter(immute_domain__in=cluster_domain_list).update(
                bk_biz_id=target_biz_id, db_module_id=db_module_id
            )
            StorageInstance.objects.filter(cluster__immute_domain__in=cluster_domain_list).update(
                bk_biz_id=target_biz_id, db_module_id=db_module_id
            )
            ProxyInstance.objects.filter(cluster__immute_domain__in=cluster_domain_list).update(
                bk_biz_id=target_biz_id, db_module_id=db_module_id
            )
            Machine.objects.filter(storageinstance__cluster__immute_domain__in=cluster_domain_list).update(
                bk_biz_id=target_biz_id, db_module_id=db_module_id
            )
            Machine.objects.filter(proxyinstance__cluster__immute_domain__in=cluster_domain_list).update(
                bk_biz_id=target_biz_id, db_module_id=db_module_id
            )
        self.log_info("transfer cluster meta to other biz success")
        return True


class TransferClusterMetaToOtherBizComponent(Component):
    name = _("迁移集群元数据")
    code = "transfer_cluster_meta_to_other_biz"
    bound_service = TransferClusterMetaToOtherBiz


class UpdateClusterDnsBelongApp(BaseService):
    """
    更新集群DNS归属业务
    """

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        target_biz_id = kwargs.get("target_biz_id")
        source_biz_id = kwargs.get("source_biz_id")
        domain_list = kwargs.get("cluster_domain_list")
        bk_cloud_id = kwargs.get("bk_cloud_id")
        param = {"app": str(source_biz_id), "new_app": str(target_biz_id), "bk_cloud_id": bk_cloud_id}

        for domain_name in domain_list:
            param["domain_name"] = domain_name
            try:
                DnsApi.update_domain_belong_app(param)
                self.log_info(_("更新dns记录成功").format(source_biz_id, target_biz_id))
            except Exception as e:  # pylint: disable=broad-except
                self.log_error(_("更新dns记录异常，相关信息: {}").format(e))
                return False

        return True


class UpdateClusterDnsBelongAppComponent(Component):
    name = _("更新dns记录")
    code = "update_cluster_dns_belong_app"
    bound_service = UpdateClusterDnsBelongApp

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

from backend import env
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.doris_resource import DorisResource
from backend.db_meta.models.storage_set_dtl import DorisResourceSet
from backend.flow.utils.doris.consts import DorisResOpType, DorisResourceGrant, DorisResourceTag
from backend.flow.utils.doris.doris_context_dataclass import DorisResourceContext

logger = logging.getLogger("flow")


class DorisResourceDBMeta(object):
    """
    根据单据信息和集群信息，对Doris集群资源管理操作写入dbmeta
    类的方法一定以Doris资源操作类型 DorisResOpType 的小写进行命名，否则不能根据类型匹配对应的方法
    """

    def __init__(self, ticket_data: dict, trans_data: any):
        """
        @param ticket_data : 单据信息
        """
        self.ticket_data = ticket_data
        self.trans_data = trans_data

    def write(self, res_op_type: DorisResOpType) -> bool:
        function_name = res_op_type.lower()
        if hasattr(self, function_name):
            return getattr(self, function_name)()

        logger.error(_("找不到Doris资源操作类型需要变更的dbmeta方法{}，请联系系统管理员").format(function_name))
        return False

    def create_bind(self) -> bool:
        # 通过集群域名获取集群实体，因创建集群flow中 cluster_id未做获取及传递
        cluster = Cluster.objects.get(immute_domain=self.ticket_data["domain"])
        if self.ticket_data["res"]["bucket_name"]:
            bucket_name = self.ticket_data["res"]["bucket_name"]
        else:
            bucket_name = getattr(self.trans_data, DorisResourceContext.get_bucket_var_name(), "")

        with atomic():
            doris_resource = DorisResource.objects.create(
                bk_biz_id=env.DBA_APP_BK_BIZ_ID,
                name=self.ticket_data["res"]["name"],
                bucket_name=bucket_name,
                region=self.ticket_data["res"]["region"],
                root_path=self.ticket_data["res"]["root_path"],
                tag=DorisResourceTag.PRIVATE.value,
                control=DorisResourceGrant.DBM.value,
            )
            DorisResourceSet.objects.create(cluster=cluster, resource=doris_resource)

        return True

    def bind_only(self) -> bool:
        # 只绑定资源与集群关系
        cluster = Cluster.objects.get(immute_domain=self.ticket_data["domain"])
        doris_resource = DorisResource.objects.get(name=self.ticket_data["res"]["name"])
        # 默认原子操作，无需添加事务
        DorisResourceSet.objects.create(cluster=cluster, resource=doris_resource)

        return True

    def untie_only(self) -> bool:
        # 只解绑资源与集群关系
        cluster = Cluster.objects.get(immute_domain=self.ticket_data["domain"])
        doris_resource = DorisResource.objects.get(name=self.ticket_data["res"]["name"])
        # 默认原子操作，无需添加事务
        DorisResourceSet.objects.filter(cluster=cluster, resource=doris_resource).delete()

        return True

    def unite_only(self) -> bool:
        # 只解绑资源与集群关系
        cluster = Cluster.objects.get(immute_domain=self.ticket_data["domain"])
        doris_resource = DorisResource.objects.get(name=self.ticket_data["res"]["name"])
        # 默认原子操作，无需添加事务
        DorisResourceSet.objects.filter(cluster=cluster, resource=doris_resource).delete()

        return True

    def untie_delete(self) -> bool:
        # 解绑资源与集群关系 及 删除资源
        cluster = Cluster.objects.get(immute_domain=self.ticket_data["domain"])
        doris_resource = DorisResource.objects.get(name=self.ticket_data["res"]["name"])

        with atomic():
            DorisResourceSet.objects.filter(cluster=cluster, resource=doris_resource).delete()
            DorisResource.objects.filter(name=self.ticket_data["res"]["name"]).delete()

        return True

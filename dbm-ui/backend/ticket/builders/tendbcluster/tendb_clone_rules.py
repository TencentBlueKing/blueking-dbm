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

from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from backend.db_services.mysql.permission.exceptions import CloneDataHasExpiredException
from backend.ticket import builders
from backend.ticket.builders.mysql.mysql_clone_rules import MySQLCloneRulesFlowParamBuilder, MySQLCloneRulesSerializer
from backend.ticket.builders.tendbcluster.base import BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TendbClusterCloneRulesSerializer(MySQLCloneRulesSerializer):
    pass


class TendbClusterCloneRulesFlowParamBuilder(MySQLCloneRulesFlowParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_CLIENT_CLONE_RULES)
class TendbClusterClientCloneRulesFlowBuilder(BaseTendbTicketFlowBuilder):
    serializer = TendbClusterCloneRulesSerializer
    class_alias = _("TenDB Cluster 客户端权限克隆执行")
    inner_flow_builder = TendbClusterCloneRulesFlowParamBuilder
    inner_flow_name = class_alias

    @property
    def need_itsm(self):
        return False

    def patch_ticket_detail(self):
        clone_uid = self.ticket.details["clone_uid"]
        data = cache.get(clone_uid)

        if not data:
            raise CloneDataHasExpiredException(_("权限克隆数据已过期，请重新提交权限克隆表单或excel文件"))

        self.ticket.update_details(clone_data=data)


@builders.BuilderFactory.register(TicketType.TENDBCLUSTER_INSTANCE_CLONE_RULES)
class TendbClusterInstanceCloneRulesFlowBuilder(TendbClusterClientCloneRulesFlowBuilder):
    class_alias = _("TenDB Cluster 实例权限克隆执行")

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
from rest_framework import serializers

from backend import env
from backend.db_meta.enums import ClusterType
from backend.db_services.mysql.permission.constants import CloneType
from backend.db_services.mysql.permission.exceptions import CloneDataHasExpiredException
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import FlowRetryType, FlowType, TicketType
from backend.ticket.models import Flow


class MySQLCloneRulesSerializer(SkipToRepresentationMixin, serializers.Serializer):
    clone_uid = serializers.CharField(help_text=_("权限克隆数据缓存uid"))
    clone_type = serializers.ChoiceField(help_text=_("权限克隆类型"), choices=CloneType.get_choices())
    cluster_type = serializers.ChoiceField(
        help_text=_("集群类型"), choices=ClusterType.get_choices(), required=False, default=ClusterType.TenDBHA
    )


class MySQLCloneRulesFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_clone_rules

    def format_ticket_data(self):
        pass

    def post_callback(self):
        excel_url = (
            f"{env.BK_SAAS_HOST}/apis/mysql/bizs/{self.ticket.bk_biz_id}/permission/clone/"
            f"get_clone_info_excel/?ticket_id={self.ticket.id}&clone_type={self.ticket.details['clone_type']}"
        )
        flow = self.ticket.current_flow()
        flow.details.update({"clone_result_excel_url": excel_url})
        flow.save(update_fields=["details"])


@builders.BuilderFactory.register(TicketType.MYSQL_CLIENT_CLONE_RULES)
class MySQLClientCloneRulesFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLCloneRulesSerializer
    class_alias = _("客户端权限克隆执行")
    inner_flow_builder = MySQLCloneRulesFlowParamBuilder
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


@builders.BuilderFactory.register(TicketType.MYSQL_INSTANCE_CLONE_RULES)
class MySQLInstanceCloneRulesFlowBuilder(MySQLClientCloneRulesFlowBuilder):
    class_alias = _("DB实例权限克隆执行")

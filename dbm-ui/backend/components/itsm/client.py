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

from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.ticket.constants import ItsmShowTable

from ..base import BaseApi
from ..domains import ITSM_APIGW_DOMAIN, ITSM_V4_APIGW_DOMAIN


class _ItsmApi(BaseApi):
    MODULE = _("ITSM流程管理")
    BASE = ITSM_APIGW_DOMAIN

    def __init__(self):
        self.create_ticket = self.generate_data_api(
            method="POST",
            url="create_ticket/",
            description=_("创建单据"),
        )
        self.get_ticket_status = self.generate_data_api(
            method="GET",
            url="get_ticket_status/",
            description=_("单据状态查询"),
        )
        self.operate_node = self.generate_data_api(method="POST", url="operate_node/", description=_("处理单据节点"))
        self.operate_ticket = self.generate_data_api(method="POST", url="operate_ticket/", description=_("处理单据"))
        self.get_ticket_info = self.generate_data_api(method="GET", url="get_ticket_info/", description=_("单据详情查询"))
        self.ticket_approval_result = self.generate_data_api(
            method="POST",
            url="ticket_approval_result/",
            description=_("审批结果查询"),
        )
        self.get_ticket_logs = self.generate_data_api(
            method="GET",
            url="get_ticket_logs/",
            description=_("单据日志查询"),
        )
        self.get_service_catalogs = self.generate_data_api(
            method="GET",
            url="get_service_catalogs/",
            description=_("服务目录查询"),
        )
        self.get_services = self.generate_data_api(method="GET", url="get_services/", description=_("服务列表查询"))
        self.create_service_catalog = self.generate_data_api(
            method="POST",
            url="create_service_catalog/",
            description=_("创建服务目录"),
        )
        self.import_service = self.generate_data_api(method="POST", url="import_service/", description=_("导入服务"))
        self.update_service = self.generate_data_api(method="POST", url="update_service/", description=_("更新服务"))


class _ItsmV4Api(BaseApi):
    MODULE = _("ITSM V4流程管理")
    BASE = ITSM_V4_APIGW_DOMAIN
    SYSTEM_ID_SETTING_KEY = SystemSettingsEnum.ITSM_V4_SYSTEM_ID.value
    WORKFLOW_KEY_SETTING_KEY = SystemSettingsEnum.ITSM_V4_WORKFLOW_KEY.value

    @classmethod
    def get_system_id(cls):
        return SystemSettings.get_setting_value(cls.SYSTEM_ID_SETTING_KEY)

    @classmethod
    def get_workflow_key(cls):
        return SystemSettings.get_setting_value(cls.WORKFLOW_KEY_SETTING_KEY)

    @classmethod
    def format_operator_value(cls, value):
        return [item.strip() for item in value.split(",") if item.strip()]

    @classmethod
    def format_text_value(cls, value):
        if value is None:
            return ""
        return str(value)

    @classmethod
    def format_dynamic_fields(cls, dynamic_fields):
        link_field = next((field for field in dynamic_fields if field.get("type") == "LINK"), {})
        string_fields = [field for field in dynamic_fields if field.get("type") == "STRING"]

        return {
            "schemes": {
                "base_table_scheme": {
                    "type": "table",
                    "attrs": {
                        "column": [
                            {
                                "name": cls.format_text_value(_("检查项")),
                                "type": "text",
                                "key": "column1",
                                "attrs": {"width": 10},
                            },
                            {
                                "name": cls.format_text_value(_("内容")),
                                "type": "text",
                                "key": "column2",
                                "attrs": {"width": 10},
                            },
                        ]
                    },
                }
            },
            "data": [
                {
                    "label": cls.format_text_value(link_field.get("name")),
                    "scheme": "base_table_scheme",
                    "extras": {"link": cls.format_text_value(link_field.get("value"))},
                    "value": [
                        {
                            "column1": {"value": cls.format_text_value(field.get("name"))},
                            "column2": {"value": cls.format_text_value(field.get("value"))},
                        }
                        for field in string_fields
                    ],
                }
            ],
        }

    @classmethod
    def format_create_ticket_params(cls, params):
        dynamic_fields = params.get("dynamic_fields", [])
        if "workflow_key" in params and "form_data" in params:
            if "approver" in params["form_data"]:
                params["form_data"]["approver"] = cls.format_operator_value(params["form_data"]["approver"])
            params["form_data"]["show_table"] = (
                ItsmShowTable.SHOW.value if dynamic_fields else ItsmShowTable.HIDE.value
            )
            return params

        form_data = {}
        for field in params.get("fields", []):
            key = field.get("key")
            if not key:
                continue
            value = field.get("value")
            if key == "title":
                key = "ticket__title"
            if key == "ticket_url":
                key = "dbm_ticket_url"
                value = {"show_text": cls.format_text_value(_("点击查看")), "url": cls.format_text_value(value)}
            if key == "approver":
                value = cls.format_operator_value(value)
            form_data[key] = value

        form_data["show_table"] = ItsmShowTable.SHOW.value if dynamic_fields else ItsmShowTable.HIDE.value
        if dynamic_fields:
            form_data["dynamic_fields"] = cls.format_dynamic_fields(dynamic_fields)

        return {
            "workflow_key": cls.get_workflow_key(),
            "operator": params.get("creator"),
            "form_data": form_data,
            "callback_url": params.get("meta", {}).get("callback_url"),
            "callback_token": params.get("callback_token"),
            "options": params.get("options", {}),
            "system_id": cls.get_system_id(),
        }

    def __init__(self):
        self.migrate_system = self.generate_data_api(
            method="POST",
            url="system/migrate/",
            description=_("V4创建/迁移系统流程"),
        )
        self.create_ticket = self.generate_data_api(
            method="POST",
            url="ticket/create/",
            description=_("V4创建工单"),
            before_request=self.format_create_ticket_params,
        )
        self.get_ticket_detail = self.generate_data_api(
            method="GET",
            url="ticket/detail/",
            description=_("V4工单详情查询"),
        )
        self.get_ticket_logs = self.generate_data_api(
            method="GET",
            url="ticket/logs/",
            description=_("V4工单日志详情查询"),
        )
        self.handle_ticket = self.generate_data_api(
            method="POST",
            url="ticket/handle/",
            description=_("V4工单处理"),
        )
        self.revoke_ticket = self.generate_data_api(
            method="POST",
            url="tickets/revoked/",
            description=_("V4工单撤销"),
        )
        self.handle_approval_node = self.generate_data_api(
            method="POST",
            url="handle_approval_node/",
            description=_("V4审批节点处理"),
        )


ItsmApi = _ItsmApi()
ItsmV4Api = _ItsmV4Api()

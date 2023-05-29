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
import copy

from backend.tests.mock_data.ticket import ticket_flow


class ItsmApiMock(object):
    """
    itsm 相关接口的mock
    """

    base_info = {"message": "success", "code": 0, "result": "true", "request_id": "0"}

    @classmethod
    def get_service_catalogs(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = [
            {
                "name": "根目录",
                "level": 0,
                "id": 100,
                "key": "test_root",
                "children": [{"name": "test", "level": 1, "id": 200, "key": "0", "children": [], "desc": "test"}],
            }
        ]

        return response_data["data"]

    @classmethod
    def create_service_catalog(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = {
            "id": 38,
            "key": "",
            "level": 1,
            "parent": 1,
            "parent_name": "根目录",
            "parent_key": "GENMULU",
            "parent__id": "2",
            "parent__name": "根目录",
            "name": "bk-dbm目录",
            "desc": "bk-dbm目录",
            "project_key": "0",
        }

        return response_data["data"]

    @classmethod
    def get_services(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = [
            {"id": 3, "name": "test1", "desc": "1", "service_type": "request"},
            {"id": 4, "name": "test2", "desc": "2", "service_type": "request"},
        ]

        return response_data["data"]

    @classmethod
    def import_service(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = {"id": 94, "name": "bk-dbm 服务", "service_type": "request", "desc": "bk-dbm 服务"}

        return response_data["data"]

    @classmethod
    def update_service(cls, *args, **kwargs):
        return cls.import_service()

    @classmethod
    def create_ticket(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = {"sn": ticket_flow.SN}

        return response_data["data"]

    @classmethod
    def ticket_approval_result(cls, *args, **kwargs):
        response_data = copy.deepcopy(cls.base_info)
        response_data["data"] = [
            {
                "sn": "REQ20200831000005",
                "title": "测试内置审批",
                "ticket_url": "https://***",
                "current_status": "FINISHED",
                "updated_by": "xx,xxx",
                "update_at": "2020-08-31 20:57:22",
                "approve_result": True,
            }
        ]

        return response_data["data"]

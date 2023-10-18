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

REMOTE_API_LIST = [
    {
        "cluster_type": "TendbCluster",
        "empty_param": [],
        "enable": True,
        "name": "shell-echo",
        "url": "tendb-cluster/shell-echo",
    },
    {
        "cluster_type": "TendbCluster",
        "empty_param": [],
        "enable": True,
        "name": "shell-counter",
        "url": "tendb-cluster/shell-counter",
    },
    {
        "cluster_type": "TendbHA",
        "empty_param": {"counter": 0},
        "enable": True,
        "name": "Counter",
        "url": "tendb-ha/counter",
    },
]

ASYNC_QUERY_DATA = [
    {
        "id": "test_id",
        "message": "",
        "error": "unexpected end of JSON input",
        "done": True,
        "start_at": "2023-08-14T09:16:37.961224+08:00",
    }
]

SESSION_ID = "test_session_id"


class CeleryServiceApiMock(object):
    """
    gse 的 mock 接口
    """

    base_info = {"result": True, "code": 0, "message": "success"}

    @classmethod
    def list(cls, *args, **kwargs):
        return REMOTE_API_LIST

    @classmethod
    def async_list(cls, *args, **kwargs):
        return REMOTE_API_LIST

    @classmethod
    def async_query(cls, *args, **kwargs):
        return ASYNC_QUERY_DATA

    @classmethod
    def async_kill(cls, *args, **kwargs):
        return ""

    @classmethod
    def _mock_celery_api1(cls, *args, **kwargs):
        return f"{SESSION_ID}_1"

    @classmethod
    def _mock_celery_api2(cls, *args, **kwargs):
        return f"{SESSION_ID}_2"

    @classmethod
    def _mock_celery_api3(cls, *args, **kwargs):
        return f"{SESSION_ID}_3"

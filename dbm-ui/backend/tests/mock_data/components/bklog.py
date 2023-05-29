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

LOG_DATA = {
    "result": True,
    "message": "查询成功",
    "data": {
        "hits": {
            "hits": [
                {
                    "_score": 2,
                    "_type": "xx",
                    "_id": "xxx",
                    "_source": {
                        "serverIp": "127.0.0.1",
                        "dtEventTimeStamp": 1565453112000,
                        "report_time": "2019-08-11 00:05:12",
                        "log": b'{"levelname": "info", "msg": "success"}',
                        "ip": "127.0.0.1",
                        "gseindex": 5857918,
                        "_iteration_idx": 3,
                        "path": "xxxxx",
                    },
                    "_index": "xxxxxxxx",
                },
                {
                    "_score": 2,
                    "_type": "xxxx",
                    "_id": "xxxxx",
                    "_source": {
                        "serverIp": "127.0.0.2",
                        "dtEventTimeStamp": 1565453113000,
                        "report_time": "2019-08-11 00:05:13",
                        "log": b'{"levelname": "info", "msg": "success"}',
                        "ip": "127.0.0.1",
                        "gseindex": 5857921,
                        "_iteration_idx": 2,
                        "path": "xxxxxxxxx",
                    },
                    "_index": "xxxxxxx",
                },
            ],
            "total": 8429903,
            "max_score": 2,
        },
        "_shards": {"successful": 9, "failed": 0, "total": 9},
        "took": 136,
        "timed_out": False,
    },
    "code": 0,
}

BK_LOG_CREATE_DATA = {
    "result": True,
    "data": {
        "collector_config_id": 358,
        "bk_data_id": 1576819,
        "subscription_id": 5869,
        "task_id_list": ["9636382"],
        "collector_config_name_en": "test",
        "collector_config_name": "test",
    },
    "code": 0,
    "message": "",
}

BK_LOG_PRE_CHECK_DATA = {
    "result": True,
    "data": {"allowed": True},
    "code": 0,
    "message": "",
}

BK_LOG_LIST_COLLECTOR_DATA = {
    "result": True,
    "data": {"total": 1, "list": [BK_LOG_CREATE_DATA["data"]]},
    "code": 0,
    "message": "",
}


class BKLogApiMock(object):
    """
    bklog相关接口的mock
    """

    @classmethod
    def esquery_search(cls, *args, **kwargs):
        data = LOG_DATA["data"]
        return data

    @classmethod
    def fast_create(cls, *args, **kwargs):
        data = BK_LOG_CREATE_DATA
        return data

    @classmethod
    def fast_update(cls, *args, **kwargs):
        data = BK_LOG_CREATE_DATA
        return data

    @classmethod
    def pre_check(cls, *args, **kwargs):
        data = BK_LOG_PRE_CHECK_DATA
        return data["data"]

    @classmethod
    def list_collectors(cls, *args, **kwargs):
        data = BK_LOG_LIST_COLLECTOR_DATA
        return data["data"]

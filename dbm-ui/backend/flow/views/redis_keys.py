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

from rest_framework.response import Response

from backend.flow.engine.controller.redis import RedisController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class RedisKeysExtractSceneApiView(FlowTestView):
    """
                api: /apis/v1/flow/scene/redis_keys_extract
               {
        "uid": "2022051612120001",
        "created_by": "xxxx",
        "bk_biz_id": "152",
        "ticket_type": "REDIS_KEYS_EXTRACT",     # 单据类型
         "fileserver": {
            "url": "制品库地址",
            "bucket": "目标bucket",
            "password": "制品库token",
            "username": "制品库username",
            "project": "制品库project"
        },
        "rules": [
            {
                "cluster_id": 1,
                "domain": "",
                "path": "/redis/keyfiles/{uid}.{domain}/",
                "white_regex": "test*",
                "black_regex": ""
            },
            {
                "cluster_id": 2,
                "domain": "",
                "path": "/redis/keyfiles/{uid}.{domain}/",
                "white_regex": "",
                "black_regex": "test*"
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = generate_root_id()
        RedisController(root_id=root_id, ticket_data=request.data).redis_keys_extract()
        return Response({"root_id": root_id})


class RedisKeysDeleteSceneApiView(FlowTestView):
    """
                api: /apis/v1/flow/scene/redis_keys_delete
               {
        "uid": "2022051612120001",
        "created_by": "xxxx",
        "bk_biz_id": "152",
        "ticket_type": "REDIS_KEYS_DELETE",
        "delete_type": "regex/files",
        "rules": [
            {
                "cluster_id": 1,
                "domain": "",
                "path" : ""，
                "total_size" : 111111,
                "white_regex": "",
                "black_regex": ""
            },
            {
                "cluster_id": 2,
                "domain": "",
                "white_regex": "",
                "black_regex": "test*"
            }
        ],
        "fileserver": {
            "url": "制品库地址",
            "bucket": "目标bucket",
            "password": "制品库token",
            "username": "制品库username",
            "project": "制品库project"
        }
    }
    """

    @staticmethod
    def post(request):
        root_id = generate_root_id()
        RedisController(root_id=root_id, ticket_data=request.data).redis_keys_delete()
        return Response({"root_id": root_id})

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
import json
import logging
import os

import jsonref
import yaml
from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger("root")


@login_exempt
@csrf_exempt
def mcp_discovery(request):
    res = __mcp_discovery()
    return JsonResponse(res if res is not None else [], safe=False)


def __mcp_discovery():
    res = []
    try:
        yaml_path = os.path.join(settings.BASE_DIR, "backend", "dbm_init", "apigw", "mcp_resources.yaml")
        with open(yaml_path, "r", encoding="utf-8") as file:
            content_str = json.dumps(yaml.safe_load(file))
            mcp_schema = copy.deepcopy(jsonref.loads(content_str))
            for tool_path, tool_info in mcp_schema["paths"].items():
                tool_schema = tool_info["post"]

                tool_operation_id = tool_schema["operationId"]
                tool_description = tool_schema["description"]
                request_schema = tool_schema["requestBody"]["content"]["application/json"]["schema"]
                response_schema = tool_schema["responses"]["200"]["content"]["application/json"]["schema"]

                res.append(
                    {
                        "path": tool_path,
                        "description": tool_description,
                        "operation_id": tool_operation_id,
                        "request_schema": request_schema,
                        "response_schema": response_schema,
                    }
                )
    except Exception as e:
        logger.warning("mcp_discovery load mcp_resources.yaml failed: %s", e)
        res = []
    return res

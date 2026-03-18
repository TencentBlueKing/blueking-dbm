# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import functools
import json
import logging
from typing import Any, Callable

from django.db import transaction
from pipeline.eri.models import Node

logger = logging.getLogger("django")


def force_skip_and_retry_decorator(field_name: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            target_node_id = kwargs.get("node_id")
            is_force = kwargs.get("is_force")
            if not target_node_id and len(args) > 1:
                target_node_id = args[1]

            original_value = None
            is_modified = False  # 标记是否真的执行了修改

            if target_node_id and is_force:
                try:
                    with transaction.atomic():
                        node_instance = Node.objects.get(node_id=target_node_id)

                        original_detail_json = json.loads(node_instance.detail)
                        original_value = original_detail_json.get(field_name)

                        if original_value is False:
                            original_detail_json[field_name] = True
                            node_instance.detail = json.dumps(original_detail_json)
                            node_instance.save()
                            is_modified = True

                except Node.DoesNotExist:
                    pass
                except Exception as e:
                    logger.error(f"[Decorator Warning] Pre-modify failed: {e}")

            try:
                return func(*args, **kwargs)
            finally:
                if target_node_id and is_modified:
                    try:
                        with transaction.atomic():
                            current_node = Node.objects.get(node_id=target_node_id)
                            current_detail = json.loads(current_node.detail)

                            # 恢复值
                            current_detail[field_name] = original_value
                            current_node.detail = json.dumps(current_detail)
                            current_node.save()
                    except Exception as e:
                        logger.error(f"[Decorator Warning] Restore failed: {e}")

        return wrapper

    return decorator

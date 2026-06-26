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

from celery.schedules import crontab

from backend.core.storages.storage import get_storage
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")

# 待清理的制品库根目录（仅清理其下内容，保留该目录本身）
STAGING_ROOT = "/staging"


def _delete_node_recursively(client, node):
    """
    删除制品库节点。目录需先清空子节点，否则 bk-repo 会返回 Folder is not empty。
    """
    full_path = node["fullPath"]
    deleted, errors = 0, 0

    if node.get("folder"):
        try:
            directories, files = client.list_dir(full_path)
        except Exception as e:  # pylint: disable=broad-except
            logger.error("[clean_staging_files] list dir failed: %s, err: %s", full_path, e)
            return deleted, errors + 1

        for child in files + directories:
            child_deleted, child_errors = _delete_node_recursively(client, child)
            deleted += child_deleted
            errors += child_errors

    try:
        client.delete_file(full_path)
        deleted += 1
        logger.info("[clean_staging_files] deleted: %s", full_path)
    except Exception as e:  # pylint: disable=broad-except
        errors += 1
        logger.error("[clean_staging_files] delete failed: %s, err: %s", full_path, e)

    return deleted, errors


@register_periodic_task(run_every=crontab(hour=0, minute=30))
def clean_staging_files_task():
    """
    每天凌晨 0:30 清理制品库 /staging 目录下的所有子目录和文件（保留 /staging 目录本身）
    """
    logger.info("[clean_staging_files] start cleaning contents under %s", STAGING_ROOT)

    # 制品库存储，使用其底层客户端直接按全路径列目录/删除节点
    storage = get_storage()
    client = storage.client

    try:
        # list_dir 返回 (目录列表, 文件列表)，元素为包含 fullPath 等信息的 dict
        directories, files = client.list_dir(STAGING_ROOT)
    except Exception as e:  # pylint: disable=broad-except
        # /staging 不存在或制品库请求异常时，记录日志并退出，不影响后续调度
        logger.warning("[clean_staging_files] skip cleaning, list dir %s failed: %s", STAGING_ROOT, e)
        return

    # 仅删除 /staging 下的一级子节点，保留 /staging 目录本身
    deleted, errors = 0, 0
    for node in directories + files:
        node_deleted, node_errors = _delete_node_recursively(client, node)
        deleted += node_deleted
        errors += node_errors

    logger.info(
        "[clean_staging_files] finished cleaning %s, deleted: %s, errors: %s",
        STAGING_ROOT,
        deleted,
        errors,
    )

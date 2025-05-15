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

from django.utils.translation import ugettext as _

from backend import env
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.flow.utils.mongodb.mongodb_repo import MongoNode

logger = logging.getLogger("root")

dev_env = str(env.REPO_VERSION_FOR_DEV)


def dev_debug(msg: str):
    """
    A simple logging function to log debug messages.
    """
    if dev_env != "":
        # Only log in dev environment
        logger.debug("env:{} msg:{}".format(dev_env, msg))


def create_failed_record(c, shard, instance, status, msg, subtype):
    """
    创建全备备份失败记录对象
    """
    logger.info(_("+===++===  create_failed_record {}, cluster_type:{} ++++++++ ".format(instance, c.cluster_type)))
    return MongodbBackupCheckReport(
        creator="",
        bk_biz_id=c.bk_biz_id,
        bk_cloud_id=c.bk_cloud_id,
        cluster=c.immute_domain,
        cluster_type=c.cluster_type,
        shard=shard,
        instance=instance,
        status=status,
        msg=msg,
        subtype=subtype,
    )


def addr(node: MongoNode) -> str:
    """
    return the address of the node in the format "ip:port"
    """
    if node is None:
        return ""
    return f"{node.ip}:{node.port}"

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
import json
import logging

from .enums import AutofixItem
from .models import RedisAutofixCtl

logger = logging.getLogger("flow")


def is_probe_deploy_biz_enabled(bk_biz_id) -> bool:
    """
    Redis 探针部署的业务白名单校验，配置存于 tb_tendis_autofix_ctl（ctl_name=probe_deploy_bizs）：
    - ctl_value == "ALL"：对所有业务生效
    - ctl_value 为 bk_biz_id 的 json 数组（如 [100, 200]）：仅对列表内的业务生效
    - 未配置 / 配置非法：默认不部署（兼容存量环境：表里没有该配置项时不报错、不写库）

    :param bk_biz_id: 单据业务 ID
    :return: 该业务是否允许部署探针
    """
    if bk_biz_id is None:
        logger.warning("probe deploy check: bk_biz_id missing, skip probe deploy")
        return False

    try:
        # bk_cloud_id / bk_biz_id 为 NOT NULL 列，初始化时必须写入（与表内其他配置项的建行惯例一致）
        item, _ = RedisAutofixCtl.objects.get_or_create(
            ctl_name=AutofixItem.PROBE_DEPLOY_BIZS.value,
            defaults={"bk_cloud_id": 0, "bk_biz_id": 0, "ctl_value": "[]"},
        )
    except Exception as err:  # noqa
        logger.warning("probe deploy biz whitelist query failed: %s, skip probe deploy", err)
        return False

    ctl_value = (item.ctl_value or "").strip()
    if ctl_value.upper() == "ALL":
        return True

    try:
        biz_ids = json.loads(ctl_value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("probe deploy biz whitelist invalid value: %s, skip probe deploy", ctl_value)
        return False

    if not isinstance(biz_ids, list):
        logger.warning("probe deploy biz whitelist expect json array, got: %s, skip probe deploy", ctl_value)
        return False

    try:
        return int(bk_biz_id) in {int(biz_id) for biz_id in biz_ids}
    except (ValueError, TypeError):
        logger.warning("probe deploy biz whitelist has invalid bk_biz_id entry: %s, skip probe deploy", ctl_value)
        return False

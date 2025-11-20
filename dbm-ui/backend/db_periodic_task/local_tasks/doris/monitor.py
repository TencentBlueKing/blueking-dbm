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
import datetime

from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS


def build_promql_query(template: str, params: list[str]) -> str:
    """
    拼接PromQL查询条件

    Args:
        template: 包含%s占位符的PromQL模板字符串
        params: 用于填充占位符的字符串数组

    Returns:
        拼接完成的PromQL查询字符串

    Example:
        >>> build_promql_query("sum(rate(%s[5m])) by (%s)", ["http_requests_total", "instance"])
        'sum(rate(http_requests_total[5m])) by (instance)'
    """
    try:
        return template % tuple(params)
    except TypeError as e:
        raise ValueError(_("参数数量与模板中的占位符不匹配")) from e


def build_query_params(query_template: dict) -> dict:
    # now-5/15m ~ now
    cur_time = datetime.datetime.now(timezone.utc)
    start_time = cur_time - datetime.timedelta(minutes=query_template["range"])

    params = copy.deepcopy(UNIFY_QUERY_PARAMS)

    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(cur_time.timestamp())

    return params


def query_promql(query_template: dict, key: str, bk_biz_id: int, clusters=None) -> dict:
    """
    调用蓝鲸监控API查询PromQL查询结果
    :param query_template:
    :param key:
    :param bk_biz_id:
    :param clusters:
    :return:
    """
    params = build_query_params(query_template)
    filters = 'appid="{}"'.format(bk_biz_id)

    # 获取指定域名的指标数据
    if clusters:
        filters = '{}, cluster_domain=~"{}"'.format(filters, "|".join(c for c in clusters))
    params["query_configs"][0]["promql"] = build_promql_query(query_template[key], [filters])
    # 调用蓝鲸监控API查询
    result = BKMonitorV3Api.unify_query(params)["series"]
    return result

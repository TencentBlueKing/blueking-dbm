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
import re

from django.utils.translation import gettext as _

from backend import env
from backend.components import BKLogApi, BKMonitorV3Api
from backend.db_monitor.constants import AUTOFIX_ACTION_NAME, AUTOFIX_ACTION_TEMPLATE
from backend.db_monitor.exceptions import BkMonitorDeleteAlarmException, BkMonitorSaveAlarmException
from backend.db_monitor.format import JsonConfigFormat
from backend.exceptions import ApiError

logger = logging.getLogger("root")


def bkm_get_alarm_strategy(name, bk_biz_id=env.DBA_APP_BK_BIZ_ID):
    """获取监控策略"""

    res = BKMonitorV3Api.search_alarm_strategy_v3(
        {
            "page": 1,
            "page_size": 100,
            "conditions": [{"key": "name", "value": name}],
            "bk_biz_id": bk_biz_id,
            "with_notice_group": False,
            "with_notice_group_detail": False,
        },
        use_admin=True,
    )
    # 批量获取策略
    for strategy in res["strategy_config_list"]:
        if strategy["name"] == name:
            return strategy


def bkm_save_alarm_strategy(params):
    """保存监控策略"""

    response = BKMonitorV3Api.save_alarm_strategy_v3(params, use_admin=True, raw=True)

    if not response.get("result"):
        if response.get("code") == BKMonitorV3Api.ErrorCode.STRATEGY_ALREADY_EXISTS:
            params["id"] = bkm_get_alarm_strategy(params["name"])["id"]
            return BKMonitorV3Api.save_alarm_strategy_v3(params, use_admin=True)
        else:
            logger.error("bkm_save_alarm_strategy failed: params: %s\n response: %s", params, response)
            raise BkMonitorSaveAlarmException(message=response.get("message"))

    return response["data"]


def bkm_delete_alarm_strategy(monitor_policy_id):
    """删除监控策略"""

    params = {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "ids": [monitor_policy_id]}
    response = BKMonitorV3Api.delete_alarm_strategy_v3(params, use_admin=True, raw=True)
    if not response.get("result"):
        logger.error("bkm_delete_alarm_strategy failed: params: %s\n response: %s", params, response)
        raise BkMonitorDeleteAlarmException(message=response.get("message"))

    logger.info("bkm_delete_alarm_strategy success: %s", monitor_policy_id)
    return response["data"]


def render_promql_sql(prom_sql, wheres):
    """
    渲染promql语句，通过正则替换
        prom_sql (str): The original PromQL query.
        wheres (dict): A dictionary of conditions to add or replace in the form {label: value or list of values}.
        example: {"appid": ["2", "3"], "cluster_domain": ["hello.2"], "db_module": ["1"]}
    """
    for label, value in wheres.items():
        # If the value is a list, convert it to a regex alternation pattern
        value = value[0] if isinstance(value, list) and len(value) == 1 else value

        # skip empty list
        if not value:
            continue

        if isinstance(value, list):
            value = f'({"|".join(map(str, value))})'
            value = f'~"{value}"'  # Use the regex match operator '~'
        else:
            value = f'"{value}"'

        # Check if label already exists in the query
        if re.search(rf'{label}="[^"]*"|\b{label}=~"[^"]*"', prom_sql):
            # If label exists, replace its value
            prom_sql = re.sub(rf'{label}="[^"]*"|\b{label}=~"[^"]*"', rf"{label}={value}", prom_sql)
        else:
            # If label does not exist, add before the closing '}'
            # Use double }} to escape a single } in the f-string
            prom_sql = re.sub(r"}", f", {label}={value}}}", prom_sql)

    return prom_sql


def get_dbm_autofix_action_id() -> int:
    """获取 dbm 故障自愈套餐 id"""
    actions = BKMonitorV3Api.search_action_config({"bk_biz_id": env.DBA_APP_BK_BIZ_ID})["data"]

    action_id = None
    for action in actions:
        if action["name"] == AUTOFIX_ACTION_NAME:
            action_id = action["id"]
    return action_id


def create_bkmonitor_action() -> int:
    """
    创建监控处理套餐
    """
    action_id = get_dbm_autofix_action_id()
    action_config = copy.deepcopy(AUTOFIX_ACTION_TEMPLATE)

    if action_id is None:
        BKMonitorV3Api.save_action_config(action_config)
    else:
        action_config["id"] = action_id
        BKMonitorV3Api.edit_action_config(action_config)
    return action_id


def create_bklog_collector(startswith: str = ""):
    bklog_json_files_path = "backend/dbm_init/json_files/bklog"
    for filename in os.listdir(bklog_json_files_path):
        if not filename.endswith(".json"):
            continue
        if not filename.startswith(startswith):
            continue

        # 读取日志采集项json文件，并渲染配置
        with open(os.path.join(bklog_json_files_path, filename), "r", encoding="utf-8") as file:
            try:
                bklog_params = json.load(file)
            except json.decoder.JSONDecodeError as err:
                logger.error(f"[create_bklog_collector] Failed to load json: {filename}, {err}")
                raise err
            log_name = filename.split(".")[0]
            # 优先获取指定了 log_name 的 formatter
            if hasattr(JsonConfigFormat, f"format_{log_name}"):
                bklog_params = JsonConfigFormat.format(bklog_params, f"format_{log_name}")
            # 根据不同 db 类型，指定对应的 formatter，主要是区分采集目标
            elif "mysql" in filename:
                bklog_params = JsonConfigFormat.format(bklog_params, JsonConfigFormat.format_mysql.__name__)
            elif "redis" in filename:
                bklog_params = JsonConfigFormat.format(bklog_params, JsonConfigFormat.format_redis.__name__)
            elif "mssql" in filename:
                bklog_params = JsonConfigFormat.format(bklog_params, JsonConfigFormat.format_mssql.__name__)
            else:
                logger.warning(_("格式化函数{log_name}不存在(如果无需格式化json可忽略)").format(log_name=log_name))

            # 针对特殊需求修改请求参数
            if hasattr(JsonConfigFormat, f"custom_modify_{log_name}"):
                bklog_params = JsonConfigFormat.custom_modify(bklog_params, f"custom_modify_{log_name}")
            # 如果存在对应的环境变量设置了日志自定义的保留天数，则进行更新
            retention = getattr(env, f"BKLOG_{log_name.upper()}_RETENTION", "") or env.BKLOG_DEFAULT_RETENTION
            bklog_params["retention"] = retention
            # 自定义了 ES 存储集群，则指定 storage_cluster_id
            if env.BKLOG_STORAGE_CLUSTER_ID:
                bklog_params["storage_cluster_id"] = env.BKLOG_STORAGE_CLUSTER_ID
            # 如果集群支持冷热数据，则补充 allocation_min_days，为 retention 的一半即可
            if env.BKLOG_CLUSTER_SUPPORT_HOT_COLD:
                bklog_params["allocation_min_days"] = retention // 2

        # 获取当前采集项的列表
        data = BKLogApi.list_collectors(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "pagesize": 500, "page": 1}, use_admin=True
        )
        collectors_name__info_map = {collector["collector_config_name_en"]: collector for collector in data["list"]}

        # 判断采集项是否重复创建
        collector_name = bklog_params["collector_config_name_en"]
        data = BKLogApi.pre_check(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "collector_config_name_en": collector_name,
            },
            use_admin=True,
        )
        if not data["allowed"]:
            # 采集项已创建，对采集项进行更新
            try:
                collector_config_id = collectors_name__info_map[collector_name]["collector_config_id"]
            except KeyError:
                logger.error(_("采集项{collector_name}被创建后删除，暂无法自动重建，请联系管理员处理。").format(collector_name=collector_name))
                continue
            bklog_params.update({"collector_config_id": collector_config_id})
            logger.info(_("采集项{collector_name}已创建, 对采集项进行更新...").format(collector_name=collector_name))
            try:
                BKLogApi.fast_update(params=bklog_params, use_admin=True)
            except ApiError as err:
                logger.error(
                    _("采集项{collector_name}更新失败，请联系管理员。错误信息：{err}").format(collector_name=collector_name, err=err)
                )

            continue

        # 创建采集项
        try:
            data = BKLogApi.fast_create(params=bklog_params, use_admin=True)
            logger.info(_("采集项创建成功，相关信息: {data}").format(data=data))
        except ApiError as err:
            # 当前采集项创建失败默认不影响下一个采集项的创建
            logger.error(_("采集项创建失败，请联系管理员。错误信息：{err}").format(err=err))

    return True

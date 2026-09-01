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
import datetime
import json
import logging
import re
import traceback

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.utils.redis import RedisConn
from backend.utils.time import date2str

from .enums import AutofixItem, MsgPriority
from .models import RedisAutofixCtl

logger = logging.getLogger("root")


def load_chat_ids_by_priority(priority: str) -> list:
    """
    读取 CHAT_IDS 配置，按优先级返回群 ID 列表。

    新格式：{"L0": [...], "L1": [...]}
    兼容旧格式：[...]（旧的纯数组，所有优先级都用同一份列表）
    """
    default_value = json.dumps({MsgPriority.L0.value: [], MsgPriority.L1.value: []})
    try:
        msg_item = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.CHAT_IDS.value).get()
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value=default_value, ctl_name=AutofixItem.CHAT_IDS.value
        ).save()
        return []

    if not msg_item or not msg_item.ctl_value:
        return []

    try:
        raw = json.loads(msg_item.ctl_value)
    except (TypeError, ValueError):
        logger.exception("parse CHAT_IDS ctl_value failed: %s", msg_item.ctl_value)
        return []

    # 兼容旧格式：list 或 已被 json.dumps 成字符串的 list
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        # 旧代码里存在 json.dumps("[]") 的情况，再解析一次
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return []
        if isinstance(raw, list):
            return raw
    if isinstance(raw, dict):
        ids = raw.get(priority, [])
        return ids if isinstance(ids, list) else []
    return []


def _decide_priority_by_title(sub_title: str) -> str:
    """
    根据消息标题自动判定优先级。
    - L0: 忽略自愈 / 自愈失败 等紧急事件
    - L1: 发起自愈 / 自愈成功 等普通信息事件

    说明: 使用正则精确匹配"事件短语",避免子串 in 判断带来的误伤
    (例如域名或备注里恰好含相同汉字)。所有 title 的模板均为
    "{immute_domain}[- ]{可选表情}{事件短语}{可选表情}", 因此
    这里只需匹配事件短语本身即可。
    """
    # L0 紧急事件正则(顺序不敏感,命中任一即视为 L0)
    # 关键词通过 _() 包裹以通过 language_finder 校验;同时切换语言时可跟随 title 一起变化
    l0_patterns = (
        re.compile(re.escape(_("忽略自愈"))),
        re.compile(re.escape(_("自愈失败"))),
    )
    for pattern in l0_patterns:
        if pattern.search(sub_title):
            return MsgPriority.L0.value
    return MsgPriority.L1.value


def send_msg_2_qywx(sub_title: str, msgs) -> bool:
    from backend.dbm_aiagent.agent.handlers import AgentHandler

    try:
        logger.info("send_msg_2_qywx start: sub_title=%s msg_keys=%s", sub_title, list(msgs.keys()))

        immute_doamin = "-".join(sub_title.split("-")[:-1])
        session_code_key = "ai|session|{}".format(immute_doamin)

        # 由本函数内部按标题判定消息优先级，调用方无需感知
        priority = _decide_priority_by_title(sub_title)
        msg_ids = load_chat_ids_by_priority(priority)
        logger.info("send_msg_2_qywx routing: priority=%s chat_ids_count=%s", priority, len(msg_ids))
        if len(msg_ids) == 0:
            logger.info("no chat ids configured for priority=%s, skip send: %s", priority, sub_title)
            return False

        bk_biz_id = msgs.get("BKID")
        if bk_biz_id is None:
            logger.warning("send_msg_2_qywx missing BKID, skip send: sub_title=%s msgs=%s", sub_title, msgs)
            return False

        db_type = DBType.Redis.value
        if msgs.get(_("集群类型"), None) in [ClusterType.MongoShardedCluster.value, ClusterType.MongoReplicaSet.value]:
            db_type = DBType.MongoDB.value

        redis_DBA = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=db_type)
        dba_user = redis_DBA[0] if redis_DBA else "admin"
        if not redis_DBA:
            logger.warning(
                "send_msg_2_qywx no dba configured, fallback to default user: bk_biz_id=%s db_type=%s",
                bk_biz_id,
                db_type,
            )

        try:
            app_info = AppCache.objects.get(bk_biz_id=bk_biz_id)
            biz_desc = "{}(#{},{})".format(app_info.bk_biz_name, app_info.bk_biz_id, app_info.db_app_abbr)
        except AppCache.DoesNotExist:
            logger.warning("send_msg_2_qywx AppCache not found: bk_biz_id=%s", bk_biz_id)
            biz_desc = "UnknownBiz(#{} )".format(bk_biz_id)

        content = _("=>>   {}\n".format(sub_title))
        for k, v in msgs.items():
            if k == "BKID":
                content += _("业务信息 : {}\n".format(biz_desc))
                content += _("业务DBA : {}(@{})\n".format(dba_user, dba_user))
            else:
                content += _("{} : {}\n".format(k, v))

        if env.ENABLE_DBM_AI and db_type == DBType.Redis.value and redis_DBA:
            session_code = RedisConn.get(session_code_key)
            ask_content = _("""查询这个{}集群最近10分钟的性能波动情况,只需给出简要的结论（再加上一个点的数据）""".format(immute_doamin))
            try:
                rest, session_code = AgentHandler.ask_agent_with_content_in_session(
                    agent_code=DBMAgentCode.REDIS_REPORT.value,
                    content=ask_content,
                    username=dba_user,
                    session_code=session_code,
                )
                RedisConn.set(session_code_key, session_code)
                content += _("{}\n".format(rest[:500]))
            except Exception as e:
                logger.exception("AI agent query failed for cluster %s: %s", immute_doamin, e)

        content += _("消息时间 : {}\n".format(date2str(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")))

        CmsiHandler(_("Tendis自愈"), content, msg_ids).send_wecom_robot_markdown()

        if not content.__contains__(_("发起")):
            RedisConn.delete(session_code_key)

        logger.info("send_msg_2_qywx success: sub_title=%s", sub_title)
        return True
    except Exception as e:
        logger.error("send_msg_2_qywx failed: sub_title=%s err=%s\n%s", sub_title, e, traceback.format_exc())
        return False


# 自愈单据级的Helpers
def get_ticket_heplers():
    helpers = []
    try:
        item = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.REDIS_HELPERS.value).get()
        if item:
            helpers = json.loads(item.ctl_value)
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value=json.dumps("[]"), ctl_name=AutofixItem.REDIS_HELPERS.value
        ).save()
    return helpers

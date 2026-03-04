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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.utils.redis import RedisConn
from backend.utils.time import date2str

from .enums import AutofixItem
from .models import RedisAutofixCtl

logger = logging.getLogger("root")


def send_msg_2_qywx(sub_title: str, msgs):
    msg_ids, immute_doamin = [], "-".join(sub_title.split("-")[:-1])
    session_code_key = "ai|session|{}".format(immute_doamin)
    try:
        msg_item = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.CHAT_IDS.value).get()
        if msg_item:
            msg_ids = json.loads(msg_item.ctl_value)
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value=json.dumps("[]"), ctl_name=AutofixItem.CHAT_IDS.value
        ).save()

    if len(msg_ids) == 0:
        return

    bk_biz_id = msgs["BKID"]
    db_type = DBType.Redis.value
    if msgs[_("集群类型")] in [ClusterType.MongoShardedCluster.value, ClusterType.MongoReplicaSet.value]:
        db_type = DBType.MongoDB.value
    redis_DBA = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=db_type)
    app_info = AppCache.objects.get(bk_biz_id=bk_biz_id)

    content = _("=>>   {}\n".format(sub_title))
    for k, v in msgs.items():
        if k == "BKID":
            content += _("业务信息 : {}(#{},{})\n".format(app_info.bk_biz_name, app_info.bk_biz_id, app_info.db_app_abbr))
            content += _("业务DBA : {}(@{})\n".format(redis_DBA[0], redis_DBA[0]))
        else:
            content += _("{} : {}\n".format(k, v))
    if db_type == DBType.Redis.value:
        session_code = RedisConn.get(session_code_key)
        ask_content = _(
            """查询这个{}集群最近10分钟的qps,mode=overall,对比看看qps是否有明显波动,只需给出简要的结论（再加上一个点的qps数据）""".format(immute_doamin)
        )
        rest, session_code = AgentHandler.ask_agent_with_content_in_session(
            agent_code=DBMAgentCode.REDIS_TASK_GUARDIAN.value,
            content=ask_content,
            username=redis_DBA[0],
            session_code=session_code,
        )
        RedisConn.set(session_code_key, session_code)
        content += _("QPS汇报 : {}\n".format(rest[:100]))
    content += _("消息时间 : {}\n".format(date2str(datetime.datetime.now(), "%Y-%m-%d %H:%M:%S")))

    CmsiHandler(_("Tendis自愈"), content, msg_ids).send_wecom_robot()

    if not content.__contains__(_("发起")):
        RedisConn.delete(session_code_key)


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

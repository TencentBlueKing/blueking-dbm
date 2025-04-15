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

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.models import AppCache
from backend.utils.time import date2str

from .enums import AutofixItem
from .models import RedisAutofixCtl

logger = logging.getLogger("root")


def send_msg_2_qywx(sub_title: str, msgs):
    msg_ids = []
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
    redis_DBA = DBAdministrator.get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Redis.value)
    app_info = AppCache.objects.get(bk_biz_id=bk_biz_id)

    content = _(">> Tendis-{}\n".format(sub_title))
    for k, v in msgs.items():
        if k == "BKID":
            content += _("业务信息 : {}(#{},{})\n".format(app_info.bk_biz_name, app_info.bk_biz_id, app_info.db_app_abbr))
            content += _("业务DBA : {}(@{})\n".format(redis_DBA[0], redis_DBA[0]))
        else:
            content += _("{} : {}\n".format(k, v))
    content += _("消息时间 : {}\n".format(date2str(datetime.datetime.now(timezone.utc), "%Y-%m-%d %H:%M:%S")))
    CmsiHandler(_("Tendis自愈"), content, msg_ids).send_wecom_robot()

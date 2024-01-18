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
from dataclasses import dataclass

from django.utils import timezone

from backend.utils.http import HttpClient
from backend.utils.time import datetime2timestamp

from .enums import AutofixItem
from .models import RedisAutofixCtl

logger = logging.getLogger("root")


@dataclass()
class MarkDownMsg:
    title: str
    subTitle: str
    app: str
    domain: str
    dba: str
    subMsg: dict

    def trans_2_markdown(self):
        if self.title != "":
            self.title = "Tendis自愈通知"

        cmt = f"""{self.title}::<font color="green">-{self.domain}-</font>-{self.subTitle}

>业务:<font color="comment">{self.app}</font>
>DBA:<font color="comment">{self.dba}<@{self.dba}></font>"""

        for k, v in self.subMsg.items():
            cmt = f"""{cmt}
>{k}:<font color="comment">{v}</font>"""

        return f"""{cmt}
消息时间: <font color="comment">{datetime2timestamp(datetime.datetime.now(timezone.utc))}</font>"""


class QyWxClient:
    def __init__(
        self,
    ):
        qywx_token, qywx_webhook = "", ""
        try:
            msg_token = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.QYWX_TOKEN.value).get()
            if msg_token:
                qywx_token = msg_token.ctl_value
        except RedisAutofixCtl.DoesNotExist:
            RedisAutofixCtl.objects.create(
                bk_cloud_id=0, bk_biz_id=0, ctl_value="", ctl_name=AutofixItem.QYWX_TOKEN.value
            ).save()
        logger.info("qywx_msg_init use token {}".format(qywx_token))

        try:
            msg_webhook = RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.QYWX_WEBHOOK.value).get()
            if msg_webhook:
                qywx_webhook = msg_webhook.ctl_value
        except RedisAutofixCtl.DoesNotExist:
            RedisAutofixCtl.objects.create(
                bk_cloud_id=0, bk_biz_id=0, ctl_value="", ctl_name=AutofixItem.QYWX_WEBHOOK.value
            ).save()
        logger.info("qywx_msg_init use hook {}".format(qywx_webhook))

        self._token = qywx_token
        self._webhook = qywx_webhook
        self._client = HttpClient()

    def send_closed(self) -> bool:
        if self._token == "" or self._webhook == "":
            return True
        return False

    def qywx_url(self) -> str:
        """构造完整的URL"""
        return f"{self._webhook}?key={self._token}"

    def send_txt_msg(self, msg: str):
        if self.send_closed():
            return

        response = self._client.request_json(
            "post", self.qywx_url(), data=json.dumps({"text": {"content": msg}, "msgtype": "text"})
        )
        print("+" * 10, response)
        if not response.get("errmsg"):
            logger.error("send_txt_msg response err: {}".format(response))
        return response

    def send_markdown_msg(self, msg: MarkDownMsg):
        if self.send_closed():
            return

        response = self._client.request_json(
            "post",
            self.qywx_url(),
            data={
                "markdown": {
                    "content": msg.trans_2_markdown(),
                    "at_short_name": True,
                },
                "msgtype": "markdown",
            },
        )
        if not response.get("errmsg"):
            logger.error("send_markdown_msg response err: {}".format(response))
        return response

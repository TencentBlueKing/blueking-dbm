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

from typing import Any, Dict, List, Tuple

from django.db import models
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import PLAT_BIZ_ID, DBType


class IPWhitelist(AuditedModel):
    bk_biz_id = models.IntegerField(_("业务ID"))
    remark = models.CharField(_("备注"), max_length=LEN_LONG)
    ips = models.JSONField(_("ip列表"))

    class Meta:
        verbose_name = _("IP白名单")
        verbose_name_plural = _("IP白名单")

    @classmethod
    def list_ip_whitelist(
        cls, filter_data: Dict[str, Any], limit: int, offset: int
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        根据业务ID获取平台以及该业务下的白名单
        @param filter_data: 过滤的字段
        @param limit: 分页限制
        @param offset: 分页起始
        """
        ips_filters = Q(bk_biz_id=PLAT_BIZ_ID) | Q(bk_biz_id=filter_data["bk_biz_id"])
        if filter_data.get("ip"):
            ips_filters = ips_filters & Q(ips__contains=filter_data["ip"])

        if filter_data.get("ids"):
            ips_filters = ips_filters & Q(id__in=filter_data["ids"])

        # IP模糊匹配
        # select_sts = "f'SELECT * FROM `bk-dbm`.configuration_ipwhitelist where ips->"$[*]" LIKE "%{filter}%"'"
        # IPWhitelist.objects.raw(select_sts)
        iplist = cls.objects.filter(ips_filters)
        count = iplist.count()
        limit = count if limit == -1 else limit
        ip_whitelist = [
            # model_to_dict没有带上create_at和update_at
            {
                "is_global": ip.bk_biz_id == PLAT_BIZ_ID,
                "create_at": ip.create_at,
                "update_at": ip.update_at,
                **model_to_dict(ip),
            }
            for ip in list(iplist[offset : limit + offset])
        ]

        return count, ip_whitelist

    @classmethod
    def batch_delete(cls, ids: List[int]):
        """
        批量删除IP白名单
        :param ids: 白名单id列表
        """
        cls.objects.filter(id__in=ids).delete()

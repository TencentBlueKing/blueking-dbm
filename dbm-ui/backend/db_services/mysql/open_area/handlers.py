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
import itertools
from collections import defaultdict
from typing import Any, Dict, List, Union

from django.utils.translation import ugettext as _

from backend.components import MySQLPrivManagerApi
from backend.db_meta.models import Cluster
from backend.db_services.mysql.open_area.exceptions import TendbOpenAreaBaseException
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig


class OpenAreaHandler:
    """封装开区的一些处理函数"""

    @classmethod
    def validate_only_openarea(cls, bk_biz_id, config_name, config_id: int = -1) -> bool:
        """校验同一业务下的开区模板名称唯一"""
        config = TendbOpenAreaConfig.objects.filter(bk_biz_id=bk_biz_id, config_name=config_name)
        is_duplicated = config.exists() and (config.first().id != config_id)
        return not is_duplicated

    @classmethod
    def openarea_result_preview(
        cls, operator: str, config_id: int, config_data: List[Dict[str, Union[int, str, Dict]]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        config = TendbOpenAreaConfig.objects.get(id=config_id)
        clusters = Cluster.objects.filter(id__in=[info["cluster_id"] for info in config_data])
        cluster_id__cluster = {cluster.id: cluster for cluster in clusters}

        # 获取开区执行数据
        openarea_results: List[Dict[str, Any]] = []
        for data in config_data:
            try:
                execute_objects = [
                    {
                        "source_db": config_rule["source_db"],
                        "target_db": config_rule["target_db_pattern"].format(**data["vars"]),
                        "schema_tblist": config_rule["schema_tblist"],
                        "data_tblist": config_rule["data_tblist"],
                        "priv_data": config_rule["priv_data"],
                        "authorize_ips": data["authorize_ips"],
                    }
                    for config_rule in config.config_rules
                ]
            except KeyError:
                raise TendbOpenAreaBaseException(_("范式渲染缺少变量"))

            openarea_results.append(
                {
                    "cluster_id": data["cluster_id"],
                    "target_cluster_domain": cluster_id__cluster[data["cluster_id"]].immute_domain,
                    "execute_objects": execute_objects,
                }
            )

        # 获取开区授权规则
        cluster_type = clusters.first().cluster_type
        priv_ids = list(itertools.chain(*[rule["priv_data"] for rule in config.config_rules]))
        authorize_rules = MySQLPrivManagerApi.list_account_rules({"bk_biz_id": config.bk_biz_id, "ids": priv_ids})
        # 根据用户名和db将授权规则分批
        user__dbs_rules: Dict[str, List[str]] = defaultdict(list)
        for rule_data in authorize_rules["items"]:
            user__dbs_rules[rule_data["account"]["user"]].extend([r["dbname"] for r in rule_data["rules"]])
        # 根据当前的规则生成授权数据
        authorize_details: List[Dict[str, Any]] = [
            {
                "bk_biz_id": config.bk_biz_id,
                "operator": operator,
                "user": user,
                "source_ips": data["authorize_ips"],
                "target_instances": [cluster_id__cluster[data["cluster_id"]].immute_domain],
                "account_rules": [
                    {"bk_biz_id": config.bk_biz_id, "dbname": dbname} for dbname in user__dbs_rules[user]
                ],
                "cluster_type": cluster_type,
            }
            for data in config_data
            for user in user__dbs_rules.keys()
        ]

        return {"config_data": openarea_results, "rules_set": authorize_details}

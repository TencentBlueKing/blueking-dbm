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
from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext

logger = logging.getLogger("flow")


class MySQLStandardizeFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = deepcopy(data)

    def doit(self):
        bk_biz_id = self.data.get("bk_biz_id")
        cluster_type = self.data.get("cluster_type")
        cluster_ids = list(set(self.data.get("cluster_ids")))
        departs = self.data.get("departs")
        with_deploy_binary = self.data.get("with_deploy_binary")
        with_push_config = self.data.get("with_push_config")
        with_collect_sysinfo = self.data.get("with_collect_sysinfo")
        with_bk_plugin = self.data.get("with_bk_plugin")
        with_cc_standardize = self.data.get("with_cc_standardize")
        with_instance_standardize = self.data.get("with_instance_standardize")

        pipe = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=cluster_ids,
        )

        pipe.add_sub_pipeline(
            sub_flow=standardize_mysql_cluster_subflow(
                root_id=self.root_id,
                data=self.data,
                bk_biz_id=bk_biz_id,
                cluster_type=cluster_type,
                cluster_ids=cluster_ids,
                departs=departs,
                with_deploy_binary=with_deploy_binary,
                with_push_config=with_push_config,
                with_collect_sysinfo=with_collect_sysinfo,
                with_bk_plugin=with_bk_plugin,
                with_cc_standardize=with_cc_standardize,
                with_instance_standardize=with_instance_standardize,
            )
        )

        logger.info(_("构建MySQL标准化流程成功"))
        pipe.run_pipeline(is_drop_random_user=True, init_trans_data_class=SystemInfoContext())

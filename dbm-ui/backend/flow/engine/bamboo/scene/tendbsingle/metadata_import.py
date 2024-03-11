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
import copy
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_modify_cluster_phase import (
    MySQLHAModifyClusterPhaseComponent,
)
from backend.flow.plugins.components.collections.tendbsingle.metadata_import import TenDBSingleImportMetadataComponent
from backend.flow.utils.mysql.mysql_context_dataclass import TenDBSingleImportMetadataContext

logger = logging.getLogger("flow")


class TenDBSingleMetadataImportFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def import_meta(self):
        import_pipe = Builder(root_id=self.root_id, data=self.data)

        import_pipe_sub = SubBuilder(root_id=self.root_id, data=self.data)

        import_pipe_sub.add_act(
            act_name=_("写入元数据"),
            act_component_code=TenDBSingleImportMetadataComponent.code,
            kwargs={**copy.deepcopy(self.data)},
        )

        import_pipe_sub.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        import_pipe_sub.add_act(
            act_name=_("修改集群状态"), act_component_code=MySQLHAModifyClusterPhaseComponent.code, kwargs={}
        )

        import_pipe.add_sub_pipeline(sub_flow=import_pipe_sub.build_sub_process(sub_name=_("TenDB Single 元数据导入")))

        logger.info(_("构建 TenDB Single 元数据导入流程成功"))
        import_pipe.run_pipeline(init_trans_data_class=TenDBSingleImportMetadataContext())

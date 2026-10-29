"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.revoke.base import RevokeFlowBase
from backend.flow.plugins.components.collections.mysql.revoke.mysql_dts_migrate_revoke import (
    MysqlDtsMigrateRevokeComponent,
)


class MysqlDtsMigrateRevokeFlow(RevokeFlowBase):
    """DTS 迁移单（三种迁移类型）被终止后，退机器单第一步「核对待退回主机」的流程。

    只有一个节点：清理本单 deploy 模式申请到的机器，并输出清理干净、可以退回资源池的主机。
    """

    def revoke_flow(self):
        """构建并启动「核对待退回主机」流程。"""
        pipeline = Builder(root_id=self.root_id, data=self.data)
        pipeline.add_act(
            act_name=_("核对待退回主机"),
            act_component_code=MysqlDtsMigrateRevokeComponent.code,
            kwargs={},
        )
        pipeline.run_pipeline()

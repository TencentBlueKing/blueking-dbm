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
from dataclasses import asdict
from typing import Dict, List

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs


def __build_trans_actuator_acts(cloud_ip_map: Dict) -> List:
    acts = []
    for bk_cloud_id, v in cloud_ip_map.items():
        ips = list(v)
        acts.append(
            {
                "act_name": _("云区域 {} 下发 actuator".format(bk_cloud_id)),
                "act_component_code": TransFileComponent.code,
                "kwargs": asdict(
                    DownloadMediaKwargs(
                        run_as_system_user=DBA_SYSTEM_USER,
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ips,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            }
        )

    return acts

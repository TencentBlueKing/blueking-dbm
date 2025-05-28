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
from typing import List

from django.utils.translation import ugettext as _

from blue_krill.data_types.enum import EnumField, StructuredEnum


class DeployPeripheralToolsDepart(str, StructuredEnum):
    # BackupClient = EnumField("backup-client", _("backup-client"))
    MySQLDBBackup = EnumField("mysql-dbbackup", _("mysql-dbbackup"))
    # 下面这些要保证和介质命名一致
    DBAToolKit = EnumField("dba-toolkit", _("dba-toolkit"))
    MySQLCrond = EnumField("mysql-crond", _("mysql-rond"))
    MySQLMonitor = EnumField("mysql-monitor", _("mysql-monitor"))
    MySQLRotateBinlog = EnumField("rotate-binlog", _("rotate-binlog"))
    MySQLTableChecksum = EnumField("mysql-checksum", _("mysql-checksum"))
    Exporter = EnumField("exporter", _("exporter"))


ALLDEPARTS = [
    # DeployPeripheralToolsDepart.BackupClient,
    DeployPeripheralToolsDepart.MySQLDBBackup,
    DeployPeripheralToolsDepart.DBAToolKit,
    DeployPeripheralToolsDepart.MySQLCrond,
    DeployPeripheralToolsDepart.MySQLMonitor,
    DeployPeripheralToolsDepart.MySQLRotateBinlog,
    DeployPeripheralToolsDepart.MySQLTableChecksum,
]


def remove_departs(
    departs: List[DeployPeripheralToolsDepart], *to_remove_departs: DeployPeripheralToolsDepart
) -> List[DeployPeripheralToolsDepart]:
    """
    不修改源 departs
    """
    res = []
    # for td in to_remove_departs:
    #     if td not in departs:
    #         res.append(td)

    for dp in departs:
        if dp not in to_remove_departs:
            res.append(dp)

    return res

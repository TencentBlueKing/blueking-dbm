"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import ugettext_lazy as _

from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.flow.consts import MYSQL_SYS_USER, ConfigTypeEnum, NameSpaceEnum, UserName
from backend.flow.utils.mysql.get_mysql_sys_user import get_mysql_sys_users


def check_client_connection(bk_cloud_id: int, instances: list, is_filter_sleep: bool = False):
    """
    通过drs接口检测实例是否存在用户线程
    @param bk_cloud_id: 操作的云区域
    @param instances: 需要判断的实例列表，每个元素的str:{ip:port}
    @param is_filter_sleep: 本次检测是否过滤sleep状态的连接，默认不过滤
    """

    # 获取内置账号名称
    admin_user_name_list = [UserName.ADMIN.value, UserName.BACKUP.value, UserName.MONITOR.value, UserName.REPL.value]
    # 对于tendb-cluster集群的实例，这里不考虑过滤内置账号的session，因为执行ddl时候，实例会存在内置账号session
    # 过滤会有风险
    users = ",".join(
        ["'" + str(x) + "'" for x in MYSQL_SYS_USER + admin_user_name_list + get_mysql_sys_users(bk_cloud_id)]
    )
    if is_filter_sleep:
        check_sql = f"select * from information_schema.processlist where command != 'Sleep' and User not in ({users})"
    else:
        check_sql = f"select * from information_schema.processlist where User not in ({users})"

    res = DRSApi.rpc(
        {
            "addresses": instances,
            "cmds": [check_sql],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )

    return res

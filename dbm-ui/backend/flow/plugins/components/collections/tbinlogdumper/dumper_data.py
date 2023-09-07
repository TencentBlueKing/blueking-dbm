"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import uuid

from pipeline.component_framework.component import Component

from backend.flow.consts import DBA_SYSTEM_USER
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.tbinlogdumper.tbinlogdumper_act_payload import TBinlogDumperActPayload


class TBinlogDumperFullSyncDataService(ExecuteDBActuatorScriptService):
    """
    针对TBinlogdumper的场景，针对库表做逻辑备份
    """

    def _execute(self, data, parent_data):

        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        backup_ip = kwargs["backup_ip"]
        backup_port = kwargs["backup_port"]
        backup_role = kwargs["backup_role"]

        # 获取需要备份的库表信息，根据TBinlogdumper设置同步信息
        dumper_conf = TBinlogDumperActPayload.get_tbinlogdumper_config(
            module_id=kwargs["module_id"], bk_biz_id=global_data["bk_biz_id"]
        )["mysqld"]

        # 拼装备份你库表正则表达式, 目前只考虑replicate_do_table 和 replicate_wild_do_table的 过滤同步场景
        backup_regex = ""
        if dumper_conf.get("replicate_do_table"):
            backup_regex = dumper_conf["replicate_do_table"].replace(",", "|")
        if dumper_conf.get("replicate_wild_do_table"):
            tmp = dumper_conf["replicate_wild_do_table"].replace("%", "*")
            backup_regex += "|"
            backup_regex += tmp.replace(",", "|")

        # 下发库表备份指令
        data.get_one_of_inputs("global_data")["port"] = backup_port
        data.get_one_of_inputs("global_data")["role"] = backup_role

        data.get_one_of_inputs("global_data")["db_table_filter_regex"] = backup_regex

        data.get_one_of_inputs("kwargs")["bk_cloud_id"] = kwargs["bk_cloud_id"]
        data.get_one_of_inputs("kwargs")[
            "get_mysql_payload_func"
        ] = TBinlogDumperActPayload.tbinlogdumper_backup_demand_payload.__name__
        data.get_one_of_inputs("kwargs")["exec_ip"] = backup_ip
        data.get_one_of_inputs("kwargs")["run_as_system_user"] = DBA_SYSTEM_USER
        return super()._execute(data, parent_data)


class TBinlogDumperFullSyncDataComponent(Component):
    name = __name__
    code = "tbinlogdumper_full_sync_data"
    bound_service = TBinlogDumperFullSyncDataService

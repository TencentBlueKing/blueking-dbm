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
import collections
import copy
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import ACCOUNT_PREFIX, DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.sleep_timer_service import SleepTimerComponent
from backend.flow.plugins.components.collections.mysql.create_user import CreateUserComponent
from backend.flow.plugins.components.collections.mysql.drop_user import DropUserComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_report import MysqlChecksumReportComponent
from backend.flow.plugins.components.collections.mysql.mysql_master_slave_relationship_check import (
    MysqlMasterSlaveRelationshipCheckServiceComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddTempUserKwargs,
    BKCloudIdKwargs,
    DownloadMediaKwargs,
    DropUserKwargs,
    ExecActuatorKwargs,
    IfTimingAfterNowKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MysqlChecksumContext

logger = logging.getLogger("flow")


class MysqlChecksumFlow(object):
    """
    数据校验pt-table-checksum单据的流程引擎

    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 9991001,
    "ticket_type": "MYSQL_CHECKSUM",
    "timing": "2022-11-21 12:04:10",
    "is_sync_non_innodb": true,
    "runtime_hour": 48
    "infos": [
        {
            "cluster_id": 2,
            "master":{"id":9,"ip":"1.1.1.1","port":20000},
            "slaves":[
            {"id":10,"ip":"2.2.2.2","port":20000}
            ],
            "db_patterns": ["db%"],
            "ignore_dbs": ["db1"],
            "table_patterns": ["t%"],
            "ignore_tables": ["tb2"]
        } ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def mysql_checksum_flow(self):
        """
        通过pt-table-checksum工具执行主从mysql实例之间的数据校验
        支持跨云管理
        增加单据临时ADMIN账号的添加和删除逻辑
        每个主库一个子流程：
        （1）检查主从关系
        （2）定时（以主库所在的集群的时区为准）
        （3）创建临时账号
        （4）dbactor执行checksum指令
        （5）删除临时账号
        （6）每个从库生成一份校验报告（如果数据不一致，生成修复单据）
        """
        cluster_ids = [i["cluster_id"] for i in self.data["infos"]]
        checksum_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipelines = []

        # 一个单据里多行任务的cluster不能重复
        masters = [
            "{}{}{}".format(job["master"]["ip"], IP_PORT_DIVIDER, job["master"]["port"]) for job in self.data["infos"]
        ]
        dup_masters = [item for item, count in collections.Counter(masters).items() if count > 1]

        if len(dup_masters) > 0:
            raise Exception("duplicate master found: {}".format(dup_masters))

        ran_str = get_random_string(length=8)
        random_account = "{}{}".format(ACCOUNT_PREFIX, ran_str)
        ran_str_obj = {"ran_str": ran_str}

        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            bk_cloud_id = cluster.bk_cloud_id
            immute_domain_obj = {"immute_domain": cluster.immute_domain}
            time_zone_obj = {"time_zone": cluster.time_zone}

            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")

            sub_pipeline = SubBuilder(
                root_id=self.root_id, data={**info, **sub_data, **ran_str_obj, **immute_domain_obj, **time_zone_obj}
            )
            sub_pipeline.add_act(
                act_name=_("检查元数据信息是否存在主备关系"),
                act_component_code=MysqlMasterSlaveRelationshipCheckServiceComponent.code,
                kwargs={},
            )
            sub_pipeline.add_act(
                act_name=_("定时"),
                act_component_code=SleepTimerComponent.code,
                kwargs=asdict(IfTimingAfterNowKwargs(True)),
            )

            acts_list = []
            for slave in info["slaves"]:
                add_temp_user_kwargs = AddTempUserKwargs(
                    bk_cloud_id=bk_cloud_id,
                    hosts=[info["master"]["ip"]],
                    user=random_account,
                    psw=ran_str,
                    address="{}{}{}".format(slave["ip"], IP_PORT_DIVIDER, slave["port"]),
                    dbname="%",
                    dml_ddl_priv="SELECT",
                    global_priv="REPLICATION CLIENT",
                )
                act_info = dict()
                act_info["act_name"] = _("创建临时用户")
                act_info["act_component_code"] = CreateUserComponent.code
                act_info["kwargs"] = asdict(add_temp_user_kwargs)
                acts_list.append(act_info)
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipeline.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=info["master"]["ip"],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("actuator执行checksum"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=info["master"]["ip"],
                        bk_cloud_id=bk_cloud_id,
                        run_as_system_user=DBA_SYSTEM_USER,
                        get_mysql_payload_func=MysqlActPayload.get_checksum_payload.__name__,
                    )
                ),
                write_payload_var="checksum_report",
            )

            acts_list = []
            for slave in info["slaves"]:
                drop_user_kwargs = DropUserKwargs(
                    bk_cloud_id=bk_cloud_id,
                    host=info["master"]["ip"],
                    user=random_account,
                    address="{}{}{}".format(slave["ip"], IP_PORT_DIVIDER, slave["port"]),
                )
                act_info = dict()
                act_info["act_name"] = _("删除临时用户")
                act_info["act_component_code"] = DropUserComponent.code
                act_info["kwargs"] = asdict(drop_user_kwargs)
                acts_list.append(act_info)
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            # 每个slave生成一个校验报告
            inner_pipelines = []
            for slave in info["slaves"]:
                inner_data = {
                    "slave_ip": slave["ip"],
                    "slave_port": slave["port"],
                    "master_ip": info["master"]["ip"],
                    "master_port": info["master"]["port"],
                }
                inner_pipeline = SubBuilder(
                    root_id=self.root_id, data={**inner_data, **info, **sub_data, **ran_str_obj}
                )
                inner_pipeline.add_act(
                    act_name=_("生成校验报告"),
                    act_component_code=MysqlChecksumReportComponent.code,
                    kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=bk_cloud_id)),
                )
                inner_pipelines.append(
                    inner_pipeline.build_sub_process(
                        sub_name=_("master[{}{}{}],slave[{}{}{}]的校验结果").format(
                            inner_data["master_ip"],
                            IP_PORT_DIVIDER,
                            inner_data["master_port"],
                            inner_data["slave_ip"],
                            IP_PORT_DIVIDER,
                            inner_data["slave_port"],
                        )
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=inner_pipelines)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(
                    sub_name=_("master[{}{}{}]的校验任务").format(
                        info["master"]["ip"], IP_PORT_DIVIDER, info["master"]["port"]
                    )
                )
            )
        checksum_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建checksum流程成功"))
        checksum_pipeline.run_pipeline(init_trans_data_class=MysqlChecksumContext(), is_drop_random_user=True)

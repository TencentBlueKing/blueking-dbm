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
from backend.flow.consts import ACCOUNT_PREFIX, DBA_SYSTEM_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.sleep_timer_service import SleepTimerComponent
from backend.flow.plugins.components.collections.mysql.create_user import CreateUserComponent
from backend.flow.plugins.components.collections.mysql.drop_user import DropUserComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_report import MysqlChecksumReportComponent
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


class SpiderChecksumFlow(object):
    """
    数据校验pt-table-checksum单据的流程引擎
    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 9991001,
    "ticket_type": "TENDBCLUSTER_CHECKSUM",
    "timing": "2022-11-21 12:04:10",
    "is_sync_non_innodb": true,
    "runtime_hour": 48,
    "infos": [
        {
            "cluster_id": 2,
            "immute_domain": "xxx",
            "time_zone": "+08:00",
            "bk_cloud_id": 0,
            "shards": [
                {
                    "shard_id": 0,
                    "master": {
                        "id": 9,
                        "ip": "1.1.1.1",
                        "port": 20000,
                        "instance_inner_role": "master"
                    },
                    "slaves": [
                        {
                            "id": 10,
                            "ip": "2.2.2.2",
                            "port": 20000,
                            "instance_inner_role": "slave"
                        }
                    ],
                    "db_patterns": [
                        "db%"
                    ],
                    "ignore_dbs": [
                        "db1"
                    ],
                    "table_patterns": [
                        "t%"
                    ],
                    "ignore_tables": [
                        "tb2"
                    ]
                }
            ]
        }
    ]}
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def spider_checksum_flow(self):
        """
        通过pt-table-checksum工具执行spider后端主从实例之间的数据校验
        支持跨云管理
        每个主库一个子流程：
        （1）定时（以主库所在的集群的时区为准）
        （2）创建临时账号
        （3）dbactor执行checksum指令
        （4）删除临时账号
        （5）每个从库生成一份校验报告（如果数据不一致，生成修复单据）
        增加单据临时ADMIN账号的添加和删除逻辑
        """

        # 一个单据里多行任务的cluster不能重复
        clusters = [job["cluster_id"] for job in self.data["infos"]]
        dup_clusters = [item for item, count in collections.Counter(clusters).items() if count > 1]

        if len(dup_clusters) > 0:
            raise Exception("duplicate cluster found: {}".format(dup_clusters))

        checksum_pipeline = Builder(
            root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=list(set(clusters))
        )
        sub_pipelines = []

        ran_str = get_random_string(length=8)
        random_account = "{}{}".format(ACCOUNT_PREFIX, ran_str)
        ran_str_obj = {"ran_str": ran_str}

        for info in self.data["infos"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("infos")
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**info, **sub_data, **ran_str_obj})

            sub_pipeline.add_act(
                act_name=_("定时"),
                act_component_code=SleepTimerComponent.code,
                kwargs=asdict(IfTimingAfterNowKwargs(True)),
            )
            masters = [shard["master"]["ip"] for shard in info["shards"]]
            sub_pipeline.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=info["bk_cloud_id"],
                        exec_ip=list(set(masters)),
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            split_pipelines = []
            for shard in info["shards"]:
                data = {**info, **shard, **sub_data, **ran_str_obj}
                split_pipeline = SubBuilder(root_id=self.root_id, data=data)
                acts_list = []
                for slave in shard["slaves"]:
                    add_temp_user_kwargs = AddTempUserKwargs(
                        bk_cloud_id=info["bk_cloud_id"],
                        hosts=[shard["master"]["ip"]],
                        user=random_account,
                        psw=ran_str,
                        address="{}{}{}".format(slave["ip"], IP_PORT_DIVIDER, slave["port"]),
                        dbname="%",
                        dml_ddl_priv="SELECT",
                        global_priv="REPLICATION CLIENT",
                    )
                    act_info = dict()
                    act_info["act_name"] = _("分片{}:创建临时用户".format(shard["shard_id"]))
                    act_info["act_component_code"] = CreateUserComponent.code
                    act_info["kwargs"] = asdict(add_temp_user_kwargs)
                    acts_list.append(act_info)
                split_pipeline.add_parallel_acts(acts_list=acts_list)

                split_pipeline.add_act(
                    act_name=_("actuator执行checksum"),
                    act_component_code=ExecuteDBActuatorScriptComponent.code,
                    kwargs=asdict(
                        ExecActuatorKwargs(
                            exec_ip=shard["master"]["ip"],
                            bk_cloud_id=info["bk_cloud_id"],
                            run_as_system_user=DBA_SYSTEM_USER,
                            get_mysql_payload_func=MysqlActPayload.get_checksum_payload.__name__,
                        )
                    ),
                    write_payload_var="checksum_report",
                )

                acts_list = []
                for slave in shard["slaves"]:
                    drop_user_kwargs = DropUserKwargs(
                        bk_cloud_id=info["bk_cloud_id"],
                        host=shard["master"]["ip"],
                        user=random_account,
                        address="{}{}{}".format(slave["ip"], IP_PORT_DIVIDER, slave["port"]),
                    )
                    act_info = dict()
                    act_info["act_name"] = _("删除临时用户")
                    act_info["act_component_code"] = DropUserComponent.code
                    act_info["kwargs"] = asdict(drop_user_kwargs)
                    acts_list.append(act_info)
                split_pipeline.add_parallel_acts(acts_list=acts_list)

                # 每个slave生成一个校验报告
                slave_pipelines = []
                for slave in shard["slaves"]:
                    inner_data = {
                        "slave_ip": slave["ip"],
                        "slave_port": slave["port"],
                        "master_ip": shard["master"]["ip"],
                        "master_port": shard["master"]["port"],
                    }
                    slave_pipeline = SubBuilder(
                        root_id=self.root_id, data={**inner_data, **info, **sub_data, **ran_str_obj}
                    )
                    slave_pipeline.add_act(
                        act_name=_("生成校验报告"),
                        act_component_code=MysqlChecksumReportComponent.code,
                        kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=info["bk_cloud_id"])),
                    )
                    slave_pipelines.append(
                        slave_pipeline.build_sub_process(
                            sub_name=_("分片{}:master[{}{}{}],slave[{}{}{}]的校验结果").format(
                                shard["shard_id"],
                                inner_data["master_ip"],
                                IP_PORT_DIVIDER,
                                inner_data["master_port"],
                                inner_data["slave_ip"],
                                IP_PORT_DIVIDER,
                                inner_data["slave_port"],
                            )
                        )
                    )
                split_pipeline.add_parallel_sub_pipeline(sub_flow_list=slave_pipelines)
                split_pipelines.append(
                    split_pipeline.build_sub_process(
                        sub_name=_(
                            "分片{}:master[{}{}{}]的校验任务".format(
                                shard["shard_id"], inner_data["master_ip"], IP_PORT_DIVIDER, inner_data["master_port"]
                            )
                        )
                    )
                )
            sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=split_pipelines)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("集群[{}]的校验任务").format(info["immute_domain"]))
            )
        checksum_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建checksum流程成功"))
        checksum_pipeline.run_pipeline(init_trans_data_class=MysqlChecksumContext(), is_drop_random_user=True)

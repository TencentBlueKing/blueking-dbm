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
import logging.config
from dataclasses import dataclass
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mongodb.add_relationship_to_meta import (
    ExecAddRelationshipOperationComponent,
)
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


# FlowActKwargs 备份、回档、清档专用.
@dataclass()
class FlowActKwargs(ActKwargs):
    def __init__(self, payload: dict):
        self.payload = payload

    @staticmethod
    def get_file_list_for_backup(cls, db_version) -> dict:
        """介质下发的kwargs"""

        file_list = GetFileList(db_type=DBType.MongoDB).mongodb_pkg(db_version=db_version)
        return {"file_list": file_list}


class MongoFakeInstallFlow(object):
    """MongoFakeInstallFlow 用作调试 不在生产环境使用"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.get_kwargs = FlowActKwargs()
        self.get_kwargs.payload = data
        self.get_kwargs.get_backup_dir()
        self.payload = data

    def start(self):
        """
        mongo_backup install流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 解析输入
        # 1. 解析每个集群Id的节点列表
        # 2. 备份一般在某个Secondary且非Backup节点上执行. 但由于无法连接mongod，这里怎么搞？
        # 3. 获得密码列表
        # 4. 生成并发子任务.
        # 介质下发——job的api可以多个IP并行执行

        # backup_dir = self.get_kwargs.get_backup_dir()
        # 复制集关系写入meta
        kwargs = self.get_add_info_to_meta_kwargs()
        logger.info("get_add_info_to_meta_kwargs return", kwargs)
        # 检查是否已存在.

        try:
            v = Cluster.objects.get(bk_biz_id=kwargs["bk_biz_id"], name=kwargs["name"])
        except Cluster.DoesNotExist:
            logging.getLogger("flow").info("pass")
            pass
        else:
            raise Exception(
                "cluster is already exists {}:{}:{}".format(kwargs["bk_biz_id"], kwargs["name"], v.cluster_type)
            )

        pipeline.add_act(
            act_name=_("MongoDB--添加关系到meta"),
            act_component_code=ExecAddRelationshipOperationComponent.code,
            kwargs=kwargs,
        )

        # 运行流程
        pipeline.run_pipeline()

    def get_add_info_to_meta_kwargs(self) -> dict:
        """添加关系到meta的kwargs"""

        info = {
            "bk_biz_id": int(self.payload["bk_biz_id"]),
            "app": self.payload["app"],
            "name": "{}-{}-{}".format(self.payload["app"], self.payload["areaId"], self.payload["setId"]),
            "alias": self.payload["alias"],
            "major_version": self.payload["db_version"],
            "creator": self.payload["created_by"],
            "bk_cloud_id": 0,
            "region": self.payload["city"],
        }

        instance_role = [
            InstanceRole.MONGO_M1,
            InstanceRole.MONGO_M2,
            InstanceRole.MONGO_M3,
            InstanceRole.MONGO_M4,
            InstanceRole.MONGO_M5,
            InstanceRole.MONGO_M6,
            InstanceRole.MONGO_M7,
            InstanceRole.MONGO_M8,
            InstanceRole.MONGO_M9,
            InstanceRole.MONGO_M10,
            InstanceRole.MONGO_BACKUP,
        ]
        if self.payload["cluster_type"] == ClusterType.MongoReplicaSet.value:
            info["cluster_type"] = ClusterType.MongoReplicaSet.value
            info["db_module_id"] = 1
            info["immute_domain"] = self.payload["nodes"][0]["domain"]
            info["storages"] = []
            if len(self.payload["nodes"]) <= 11:
                for index, node in enumerate(self.payload["nodes"]):
                    if index == len(self.payload["nodes"]) - 1:
                        info["storages"].append(
                            {
                                "role": InstanceRole.MONGO_BACKUP,
                                "ip": node["ip"],
                                "port": node["port"],
                                "domain": node["domain"],
                            }
                        )
                    else:
                        info["storages"].append(
                            {
                                "role": instance_role[index],
                                "ip": node["ip"],
                                "port": node["port"],
                                "domain": node["domain"],
                            }
                        )
        else:
            raise Exception("bad cluster_type {}".format(self.payload["cluster_type"]))
        return info

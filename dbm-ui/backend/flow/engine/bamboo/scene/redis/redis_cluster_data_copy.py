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
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.redis_dts.enums import DtsBillType, DtsCopyType, DtsWriteMode
from backend.db_services.redis_dts.util import complete_redis_dts_kwargs_dst_data, complete_redis_dts_kwargs_src_data
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs.redis_dts import (
    RedisDtsDataCopyAtomJob,
    RedisDtsDstClusterBackupAndFlush,
)
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, RedisDtsContext

logger = logging.getLogger("flow")


class RedisClusterDataCopyFlow(object):
    """
    redis集群数据复制
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data
        self.precheck()

    def redis_cluster_data_copy_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        bk_biz_id = self.data["bk_biz_id"]
        write_mode = self.data["write_mode"]
        dts_copy_type = self.__get_dts_copy_type()
        for info in self.data["infos"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = RedisDtsContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.cluster = {}
            act_kwargs.cluster["dts_bill_type"] = self.data["ticket_type"]
            act_kwargs.cluster["dts_copy_type"] = dts_copy_type
            act_kwargs.cluster["info"] = info
            complete_redis_dts_kwargs_src_data(bk_biz_id, dts_copy_type, info, act_kwargs)
            complete_redis_dts_kwargs_dst_data(self.__get_dts_biz_id(info), dts_copy_type, info, act_kwargs)

            if (
                dts_copy_type != DtsCopyType.COPY_TO_OTHER_SYSTEM
                and write_mode == DtsWriteMode.FLUSHALL_AND_WRITE_TO_REDIS
            ):
                redis_pipeline.add_sub_pipeline(RedisDtsDstClusterBackupAndFlush(self.root_id, self.data, act_kwargs))

            redis_pipeline.add_sub_pipeline(RedisDtsDataCopyAtomJob(self.root_id, self.data, act_kwargs))
        # redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def __get_dts_copy_type(self) -> str:
        if self.data["ticket_type"] in [
            DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
            DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
        ]:
            return ""
        else:
            return self.data["dts_copy_type"]

    def __get_dts_biz_id(self, info: dict) -> int:
        if (
            self.data["ticket_type"] == DtsBillType.REDIS_CLUSTER_DATA_COPY
            and self.data["dts_copy_type"] == DtsCopyType.DIFF_APP_DIFF_CLUSTER
        ):
            return info["dst_bk_biz_id"]
        else:
            return self.data["bk_biz_id"]

    def precheck(self):
        src_cluster_set: set = set()
        bk_biz_id = self.data["bk_biz_id"]
        dts_copy_type = self.__get_dts_copy_type()
        for info in self.data["infos"]:
            if info["src_cluster"] in src_cluster_set:
                raise Exception(_("源集群{}重复了").format(info["src_cluster"]))
            src_cluster_set.add(info["src_cluster"])

            if dts_copy_type != DtsCopyType.USER_BUILT_TO_DBM.value:
                try:
                    Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
                except Cluster.DoesNotExist:
                    raise Exception("src_cluster {} does not exist".format(info["src_cluster"]))

            if dts_copy_type != DtsCopyType.COPY_TO_OTHER_SYSTEM.value:
                try:
                    Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["dst_cluster"]))
                except Cluster.DoesNotExist:
                    raise Exception("dst_cluster {} does not exist".format(info["dst_cluster"]))

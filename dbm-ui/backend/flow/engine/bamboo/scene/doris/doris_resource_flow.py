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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.doris_resource import DorisResource
from backend.db_meta.models.storage_set_dtl import DorisResourceSet
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import DorisBaseFlow
from backend.flow.plugins.components.collections.doris.doris_cos_manage import CosManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.resource_db_meta import DorisResourceMetaComponent
from backend.flow.utils.doris.consts import (
    DORIS_BUCKET_NAME_MAX_LENGTH,
    DORIS_RES_NAME_MAX_LENGTH,
    DORIS_RES_NAME_TMPL,
    DorisResOpType,
    DorisResourceTag,
)
from backend.flow.utils.doris.doris_act_payload import DorisActPayload, get_key_by_account_id
from backend.flow.utils.doris.doris_context_dataclass import DorisActKwargs, DorisResourceContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DorisResourceFlow(DorisBaseFlow):
    """
    构建Doris集群远程(冷)存储资源管理子流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.root_id = root_id
        self.data = data
        # 获取存储桶所属地域
        cos_regeion_map = SystemSettings.get_setting_value(key=SystemSettingsEnum.DORIS_COS_REGION, default={})
        cos_region = cos_regeion_map.get(data["city_code"], "")
        self.data["cos_region"] = cos_region
        # 获取公共存储桶信息
        public_res = DorisResource.objects.filter(
            region=cos_region,
            tag=DorisResourceTag.PUBLIC,
            bk_cloud_id=data["bk_cloud_id"],
        ).first()
        if public_res:
            # 若公共存储桶存在，将model转为字典存入
            self.data["public_res"] = model_to_dict(public_res)

        if data.get("private_res_name"):
            private_res = DorisResource.objects.get(name=data["private_res_name"])
            self.data["private_res"] = model_to_dict(private_res)

    def create_resource_sub_flow(self, data: dict) -> SubBuilder:
        """
        内网创建Doris资源及绑定的子流程
        """
        create_res_data = copy.deepcopy(data)

        # 通过大数据子账号 从密码服务获取AK/SK
        cloud_auth = get_key_by_account_id(account_id=env.BIGDATA_CLOUD_ACCOUNT_ID)

        # 资源名称长度需要确认, 由Doris集群限制, 64位
        res_name = gen_resource_name(bk_biz_id=data["bk_biz_id"], cluster_name=data["cluster_name"])
        # 生成bucket_name
        # bucket_name长度，COS限制共30个字符
        bucket_name = gen_buckect_name(res_name=res_name, cos_app_id=cloud_auth["appid"])
        # 将创建资源需要的字段写到data
        res = {
            "account_id": env.BIGDATA_CLOUD_ACCOUNT_ID,
            "region": data["cos_region"],
            "name": res_name,
            "access_key": cloud_auth["access_key"],
            "secret_key": cloud_auth["secret_key"],
            "root_path": f"/{res_name}",
            "bucket_name": bucket_name,
        }
        create_res_data["res"] = res
        create_res_sub_pipeline = SubBuilder(root_id=self.root_id, data=create_res_data)
        create_res_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        create_res_kwargs.set_trans_data_dataclass = DorisResourceContext.__name__
        create_res_kwargs.res_op_type = DorisResOpType.CREATE_AND_BIND.value

        create_res_sub_pipeline.add_act(
            act_name=_("Doris资源管理-获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(create_res_kwargs),
        )
        # 1. 创建COS资源
        create_res_sub_pipeline.add_act(
            act_name=_("创建冷存储资源"), act_component_code=CosManageComponent.code, kwargs=asdict(create_res_kwargs)
        )
        # 2. 调用actor接口绑定Doris资源
        create_res_kwargs.exec_ip = create_res_data["master_fe_ip"]
        create_res_kwargs.get_doris_payload_func = DorisActPayload.get_create_resource_payload.__name__
        create_res_sub_pipeline.add_act(
            act_name=_("Doris绑定远程存储资源"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(create_res_kwargs),
        )
        # 3. 写入dbmeta
        create_res_sub_pipeline.add_act(
            act_name=_("更新集群资源关系到DBMeta"),
            act_component_code=DorisResourceMetaComponent.code,
            kwargs=asdict(create_res_kwargs),
        )

        return create_res_sub_pipeline

    def bind_exist_resource_sub_flow(self, data: dict, res_info: dict) -> SubBuilder:
        """
        绑定已存在的资源 子流程：适用于绑定公共资源，外部环境已创建的独立集群资源
        """
        sub_flow_data = copy.deepcopy(data)
        # 已存在的资源，需要获取ak/sk 写到sub_flow_data中
        if res_info.get("account_id"):
            account_id = res_info["account_id"]
        else:
            account_id = env.BIGDATA_CLOUD_ACCOUNT_ID
        cloud_auth = get_key_by_account_id(account_id=account_id)
        res_info["access_key"] = cloud_auth["access_key"]
        res_info["secret_key"] = cloud_auth["secret_key"]

        sub_flow_data["res"] = res_info
        bind_exist_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        bind_exist_kwargs.set_trans_data_dataclass = DorisResourceContext.__name__
        bind_exist_kwargs.res_op_type = DorisResOpType.BIND_ONLY.value
        bind_exist_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)

        bind_exist_sub_pipeline.add_act(
            act_name=_("Doris资源管理-获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(bind_exist_kwargs),
        )

        # 1. 调用actor接口绑定Doris资源
        bind_exist_kwargs.exec_ip = sub_flow_data["master_fe_ip"]
        bind_exist_kwargs.get_doris_payload_func = DorisActPayload.get_create_resource_payload.__name__
        bind_exist_sub_pipeline.add_act(
            act_name=_("Doris绑定远程存储资源"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(bind_exist_kwargs),
        )
        # 2. 写入dbmeta
        bind_exist_sub_pipeline.add_act(
            act_name=_("更新集群资源关系到DBMeta"),
            act_component_code=DorisResourceMetaComponent.code,
            kwargs=asdict(bind_exist_kwargs),
        )
        return bind_exist_sub_pipeline

    def untie_resource_sub_flow(self, data: dict, res_info: dict) -> SubBuilder:
        """
        解绑资源 子流程 (缩容/下架)
        """
        sub_flow_data = copy.deepcopy(data)
        sub_flow_data["res"] = res_info
        untie_res_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        untie_res_kwargs.set_trans_data_dataclass = DorisResourceContext.__name__
        untie_res_kwargs.res_op_type = DorisResOpType.UNTIE_ONLY.value
        untie_res_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)

        untie_res_sub_pipeline.add_act(
            act_name=_("Doris资源管理-获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(untie_res_kwargs),
        )
        # 1. 调用actor接口解绑Doris资源
        if not data["ticket_type"] == TicketType.DORIS_DESTROY.value:
            untie_res_kwargs.exec_ip = sub_flow_data["master_fe_ip"]
            untie_res_kwargs.get_doris_payload_func = DorisActPayload.get_drop_resource_payload.__name__
            untie_res_sub_pipeline.add_act(
                act_name=_("Doris删除远程存储资源"),
                act_component_code=ExecuteDorisActuatorScriptComponent.code,
                kwargs=asdict(untie_res_kwargs),
            )
        # 2. 写入dbmeta
        untie_res_sub_pipeline.add_act(
            act_name=_("更新集群资源关系到DBMeta"),
            act_component_code=DorisResourceMetaComponent.code,
            kwargs=asdict(untie_res_kwargs),
        )
        return untie_res_sub_pipeline

    def delete_resource_sub_flow(self, data: dict, res_info: dict) -> SubBuilder:
        """
        解绑+删除资源 子流程
        """
        sub_flow_data = copy.deepcopy(data)
        sub_flow_data["res"] = res_info
        delete_res_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        delete_res_kwargs.set_trans_data_dataclass = DorisResourceContext.__name__
        delete_res_kwargs.res_op_type = DorisResOpType.UNTIE_AND_DELETE.value
        delete_res_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)

        delete_res_sub_pipeline.add_act(
            act_name=_("Doris资源管理-获取Payload"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(delete_res_kwargs),
        )
        # 1. 调用actor接口解绑Doris资源
        """
        # 在下架删除(destroy)流程里, Doris服务已停止(disable), 解绑动作无法(亦无须)完成
        # 1). 通过单据类型判断是否跳过该步骤
        # 2). 由于shrink单据也会调用该子流程，此时Doris服务应正常响应
        """
        if not data["ticket_type"] == TicketType.DORIS_DESTROY.value:
            delete_res_kwargs.exec_ip = sub_flow_data["master_fe_ip"]
            delete_res_kwargs.get_doris_payload_func = DorisActPayload.get_drop_resource_payload.__name__
            delete_res_sub_pipeline.add_act(
                act_name=_("Doris解绑远程存储资源"),
                act_component_code=ExecuteDorisActuatorScriptComponent.code,
                kwargs=asdict(delete_res_kwargs),
            )
        # 2 删除资源
        delete_res_sub_pipeline.add_act(
            act_name=_("删除冷存储资源"), act_component_code=CosManageComponent.code, kwargs=asdict(delete_res_kwargs)
        )
        # 3. 写入dbmeta
        delete_res_sub_pipeline.add_act(
            act_name=_("更新集群资源关系到DBMeta"),
            act_component_code=DorisResourceMetaComponent.code,
            kwargs=asdict(delete_res_kwargs),
        )

        return delete_res_sub_pipeline

    def shrink_resource_sub_flow(self, data: dict) -> SubBuilder:
        """
        TODO 缩容资源子流程暂不实现
        """
        sub_flow_data = copy.deepcopy(data)

        shrink_res_sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_data)
        return shrink_res_sub_pipeline

    def data_exist_public_resource(self) -> bool:
        """
        判断单据data中是否存在公共资源
        """
        return self.data.get("public_res")

    def data_exist_private_resource(self) -> bool:
        """
        判断单据data中是否存在独立资源
        """
        return self.data.get("private_res")

    # 判断cluster是否存在独立集群资源
    def cluster_exists_private_resource(self) -> bool:
        # 保持使用data承载属性，不使用对象属性
        cluster = Cluster.objects.get(id=self.data.get("cluster_id"))
        exists = DorisResourceSet.objects.filter(
            cluster=cluster, resource__tag=DorisResourceTag.PRIVATE.value
        ).exists()
        return exists

    def cluster_exists_public_resource(self) -> bool:
        # 保持使用data承载属性，不使用对象属性
        cluster = Cluster.objects.get(id=self.data.get("cluster_id"))
        exists = DorisResourceSet.objects.filter(cluster=cluster, resource__tag=DorisResourceTag.PUBLIC.value).exists()
        return exists

    def cluster_exists_resource(self, res_tag: DorisResourceTag) -> bool:
        # 保持使用data承载属性，不使用对象属性
        exists = DorisResourceSet.objects.filter(
            cluster_id=self.data["cluster_id"], resource__tag=res_tag.value
        ).exists()
        return exists


def check_doris_resource_env() -> bool:
    """
    检查创建Doris资源需要的环境变量参数是否满足
    """
    if env.HCM_COS_ACCOUNT_ID and env.COS_INTERNAL_ENDPOINT_TMPL and env.COS_SERVICE_DOMAIN:
        return True
    return False


def gen_resource_name(bk_biz_id: int, cluster_name: str) -> str:
    """
    生成Doris资源名称。
    通过业务ID + 集群名称拼接，需按Doris集群限制截断长度
    """
    whole_name = DORIS_RES_NAME_TMPL.format(bk_biz_id=bk_biz_id, cluster_name=cluster_name)

    return whole_name[:DORIS_RES_NAME_MAX_LENGTH]


def gen_buckect_name(res_name: str, cos_app_id: str) -> str:
    """
    生成Doris创建COS存储桶名称。
    通过资源名称(包含dbm标记，业务ID标记，集群名标记), 拼接上对应的云APPID(腾讯云限制，必须)
    """
    sep = "-"
    max_prefix_length = DORIS_BUCKET_NAME_MAX_LENGTH - len(sep) - len(cos_app_id)
    if max_prefix_length < 0:
        # 说明cos_app_id + '-' 本身就超过限制，无法满足要求
        raise ValueError("cos_app_id too long to fit with separator within limit")

    # 截断res_name
    truncated_prefix = res_name[:max_prefix_length]

    return f"{truncated_prefix}{sep}{cos_app_id}"


def get_cluster_res(cluster_id: int, res_tag: DorisResourceTag) -> dict:
    res_set = DorisResourceSet.objects.filter(cluster_id=cluster_id, resource__tag=res_tag.value)
    res = res_set.first().resource if res_set.exists() else None
    return model_to_dict(res)

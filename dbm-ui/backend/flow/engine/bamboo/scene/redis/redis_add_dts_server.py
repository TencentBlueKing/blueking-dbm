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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.core.encrypt.constants import RSAConfigType
from backend.core.encrypt.handlers import RSAHandler
from backend.db_proxy.models import DBCloudProxy
from backend.flow.consts import CloudServiceName, ConfigFileEnum, ConfigTypeEnum, NameSpaceEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_dts_server_meta import RedisDtsServerMetaComponent
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisAddDtsServerFlow(object):
    """
    Redis 添加 DTS Server
    """

    def __init__(self, root_id, data):
        self.root_id = root_id
        self.data = data

    def redis_add_dts_server_flow(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        sub_pipelines = []
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_add_dts_server()
        act_kwargs.is_update_trans_data = True

        for info in self.data["infos"]:
            """
            info: {"ip": "3.3.3.1", "bk_cloud_id": 0, "bk_host_id": 2,"bk_city_name":"上海"}
            """
            logger.info("redis_add_dts_server_flow info:{}".format(info))
            nginx_url = self.__get_cloud_nginx_url(info["bk_cloud_id"])
            cloud_token = self.__get_cloud_token(info["bk_cloud_id"])
            system_user_info = self.__get_system_user_info(self.data["bk_biz_id"])

            cluster = {
                **info,
                "nginx_url": nginx_url,
                "cloud_token": cloud_token,
                **system_user_info,
            }
            act_kwargs.cluster = cluster
            act_kwargs.exec_ip = info["ip"]
            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-下发介质").format(info["ip"]),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipeline.add_act(
                act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
            )

            sub_pipeline.add_act(
                act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
            )

            act_kwargs.get_redis_payload_func = RedisActPayload.get_add_dts_server_payload.__name__
            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-部署").format(info["ip"]),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

            sub_pipeline.add_act(
                act_name=_("DTS_Server-{}-写入dbmeta").format(info["ip"]),
                act_component_code=RedisDtsServerMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

        sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("ADD DTS_SERVER")))
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def __get_cloud_nginx_url(self, bk_cloud_id):
        """
        获取云区域nginx地址
        """
        nginx = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last()
        return "http://{}".format(nginx.internal_address)

    def __get_cloud_token(self, bk_cloud_id) -> str:
        """
        获取云区域token
        """
        service_type = CloudServiceName.RedisDTS.value
        db_cloud_token = f"{bk_cloud_id}_{service_type}_token"
        rsa = RSAHandler.get_or_generate_rsa_in_db(RSAConfigType.PROXYPASS.value)
        return RSAHandler.encrypt_password(rsa.rsa_public_key.content, db_cloud_token)

    def __get_system_user_info(self, bk_biz_id):
        """
        获取云区域系统用户信息
        """
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": bk_biz_id,
                "level_name": LevelName.APP,
                "level_value": bk_biz_id,
                "conf_file": ConfigFileEnum.OS,
                "conf_type": ConfigTypeEnum.OSConf,
                "namespace": NameSpaceEnum.Common,
                "format": FormatType.MAP,
            }
        )
        return {"system_user": data["content"]["user"], "system_password": data["content"]["user_pwd"]}

"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from backend.components import DBConfigApi


class DbConfigNameDef:
    def __init__(
        self,
        namespace,
        conf_type,
        conf_file,
        conf_name,
        value_default,
        value_allowed,
        value_type,
        value_type_sub,
        need_restart,
        flag_visible,
        flag_readonly,
        flag_locked,
        flag_encrypt,
        conf_name_lc,
        description,
    ):
        self.namespace = namespace
        self.conf_type = conf_type
        self.conf_file = conf_file
        self.conf_name = conf_name
        self.value_default = value_default
        self.value_allowed = value_allowed
        self.value_type = value_type
        self.value_type_sub = value_type_sub
        self.need_restart = need_restart
        self.flag_visible = flag_visible
        self.flag_readonly = flag_readonly
        self.flag_locked = flag_locked
        self.flag_encrypt = flag_encrypt
        self.conf_name_lc = conf_name_lc
        self.description = description

    def upsert(self):
        params = {
            "namespace": self.namespace,
            "conf_type": self.conf_type,
            "conf_file": self.conf_file,
            "conf_names": [
                {
                    "conf_name": self.conf_name,
                    "value_default": self.value_default,
                    "value_allowed": self.value_allowed,
                    "value_type": self.value_type,
                    "value_type_sub": self.value_type_sub,
                    "need_restart": self.need_restart,
                    "flag_visible": self.flag_visible,
                    "flag_readonly": self.flag_readonly,
                    "flag_locked": self.flag_locked,
                    "flag_encrypt": self.flag_encrypt,
                    "conf_name_lc": self.conf_name_lc,
                    "description": self.description,
                }
            ],
        }

        # Call API
        try:
            DBConfigApi.change_plat_config(params=params)
        except Exception as e:
            print(e)
            return False


class DbConfigGenerate:
    """
    生成dbconfig，简化参数
    :param namespace: 命名空间
    :param conf_type: 配置类型
    :param conf_file: 配置文件
    :param bk_biz_id: 业务ID
    :param db_module_id: 数据库模块ID
    :param cluster_domain: 集群域名
    """

    def __init__(self, namespace, conf_type, conf_file, bk_biz_id, db_module_id, cluster_domain):
        self.namespace = namespace
        self.conf_type = conf_type
        self.conf_file = conf_file
        self.bk_biz_id = bk_biz_id
        self.db_module_id = db_module_id
        self.cluster_domain = cluster_domain

    def generate(self):
        body_param = {
            "namespace": self.namespace,
            "conf_type": self.conf_type,
            "conf_file": self.conf_file,
            "method": "GenerateAndPublish",
            "format": "map.",
            "level_name": "cluster",
            "level_value": self.cluster_domain,
            "bk_biz_id": str(self.bk_biz_id),
            "level_info": {
                "module": str(self.db_module_id),
            },
        }
        try:
            DBConfigApi.get_or_generate_instance_config(body_param)
        except Exception as e:
            print(e)

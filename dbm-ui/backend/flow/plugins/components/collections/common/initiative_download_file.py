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

from jinja2 import Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkShortJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

download_script_content = """
    #/bin/bash 
    if [ ! -f /data/install/dbactuator ];then
        cd /data/install/&& wget --header "Host:{{domain}}" --tries=10  {{file_url}} -o dbactuator 
        if [ $? -eq 0 ];then
            echo "download dbactor success"
            exit 0
        fi
    fi
    dbactormd5=$(md5sum /data/install/dbactuator | awk '{print $1}')
    if [ "$dbactormd5" != "{{new_dbactor_md5sum}}" ]; then
        echo "dbactormd5 is not equal to {{new_dbactor_md5sum}}, will download replace dbactor"
        cd /data/install/ && rm -rf dbactuator && wget  --header "Host:{{domain}}" --tries=10  {{file_url}} -O dbactuator
        if [ $? -eq 0 ];then
            echo "download dbactor success"
            exit 0
        else
            echo "download dbactor failed"
            exit 1
        fi
    else
        echo "dbactormd5 is equal to {{new_dbactor_md5sum}}, no need to download replace dbactor"
    fi
"""  # noqa


class InitiativeDownloadFile(BkShortJobService):
    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs.get("get_trans_data_ip_var"):
            exec_ips = self.splice_exec_ips_list(pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"]))
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")
        file_url = kwargs["file_url"]
        new_dbactor_md5sum = kwargs["md5sum"]
        domain = env.BKREPO_ENDPOINT_URL.replace("https://", "").replace("http://", "").rstrip("/")
        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(download_script_content)
        script_content = template.render(
            file_url=file_url,
            new_dbactor_md5sum=new_dbactor_md5sum,
            domain=domain,
        )

        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "initiative_download_file",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("ready start task with body {}".format(body))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")
        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class InitiativeDownloadFileComponent(Component):
    name = __name__
    code = "initiative_download_file"
    bound_service = InitiativeDownloadFile

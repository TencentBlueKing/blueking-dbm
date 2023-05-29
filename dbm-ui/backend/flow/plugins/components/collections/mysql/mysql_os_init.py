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
import base64
import copy
import re

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi
from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs

cenos_script_content = """
    #/bin/bash 
    FOUND=$(grep nofile /etc/security/limits.conf |grep -v "#") 
    if [ ! -z "$FOUND" ]; then 
        sed -i '/ nofile /s/^/#/' /etc/security/limits.conf 
    fi 
    PKGS=("perl" "perl-Digest-MD5" "perl-Test-Simple" "perl-DBI" "perl-DBD-MySQL" "perl-Data-Dumper" "perl-Encode" "perl-Time-HiRes" "perl-JSON")
    for pkg in  ${PKGS[@]} 
    do 
        if rpm -q ${pkg} &> /dev/null;then 
            echo "$pkg already install" 
            continue 
        fi 
        yum install -y ${pkg}   
    done
"""  # noqa


class MySQLOsInit(BkJobService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        os_type = kwargs["os_type"]
        bk_biz_id = kwargs["bk_biz_id"]
        if re.match("centos", os_type, re.I):
            script_content = cenos_script_content
        else:
            script_content = cenos_script_content

        target_ip_info = kwargs["ip_list"]
        ips = []
        for info in target_ip_info:
            ips.append(info["ip"])
        body = {
            "bk_biz_id": bk_biz_id,
            "task_name": f"DBM_MySQL_OS_Init",
            "script_content": str(base64.b64encode(script_content.encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("ready start task with body {}".format(body))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER

        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url:{env.BK_JOB_URL}/api_execute/{resp['data']['job_instance_id']}")
        # 传入调用结果，并单调监听任务状态
        data.outputs.ext_result = resp
        data.outputs.exec_ips = ips
        return True


class MySQLOsInitComponent(Component):
    name = __name__
    code = "mysql_os_init"
    bound_service = MySQLOsInit

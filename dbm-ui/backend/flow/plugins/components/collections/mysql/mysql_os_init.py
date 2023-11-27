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

from jinja2 import Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import JobApi, MySQLPrivManagerApi
from backend.flow.consts import DBA_ROOT_USER, DEFAULT_INSTANCE, MySQLPrivComponent, UserName
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs

cpl = re.compile("<ctx>(?P<context>.+?)</ctx>")

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
    ret=`perldoc -l Digest::MD5`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find Digest::MD5"
    fi
    ret=`perldoc -l Data::Dumper`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find Data::Dumper"
    fi
    ret=`perldoc -l  JSON`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find JSON"
    fi
    ret=`perldoc -l  DBD::mysql`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find DBD::mysql"
    fi
    ret=`perldoc -l  DBI`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find DBI"
    fi
    ret=`perldoc -l Encode`
    if [[  $ret =~ "No documentation found" ]]
    then
        echo "not not find Encode"
    fi
"""  # noqa


class MySQLOsInit(BkJobService):
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
        os_name = "centos"  # kwargs["os_name"]
        if re.search("centos", os_name, re.I) is not None:
            script_content = cenos_script_content
        else:
            # 待补充其他os的初始化脚本
            script_content = cenos_script_content

        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM_MySQL_OS_Init",
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
        data.outputs.exec_ips = exec_ips
        return True


class MySQLOsInitComponent(Component):
    name = __name__
    code = "mysql_os_init"
    bound_service = MySQLOsInit


# 异步 I/O（AIO）操作的最大并发请求数
# fs.aio-max-nr=1024000
os_sysctl_init = """
    #/bin/bash 
    egrep "^mysql" /etc/group >& /dev/null
    if [ $? -ne 0 ]
    then
    groupadd mysql -g 202
    fi
    id mysql >& /dev/null
    if [ $? -ne 0 ]
    then
            useradd -m -d /home/mysql -g 202 -G users -u 30019 mysql
            chage -M 99999 mysql
            if [ ! -d /home/mysql ]; 
            then
                    mkdir -p /home/mysql
            fi
            chmod 755 /home/mysql
            usermod -d /home/mysql mysql
    fi
    # if there is a mysql user an error will be reported in the previous step and home mysql will not be created so make a judgment and create home mysql
    if [ ! -d /data ];
    then
        mkdir -p /data1/data/
        ln -s /data1/data/ /data
    fi
    if [ ! -d /data1 ];
    then
        mkdir -p /data/data1/
        ln -s /data/data1 /data1
    fi
    mkdir -p /data1/dbha
    chown -R mysql /data1/dbha
    mkdir -p /data/dbha
    chown -R mysql /data/dbha
    #mkdir -p /home/mysql/install
    #chown -R mysql /home/mysql
    #chmod -R a+rwx /home/mysql/install
    mkdir -p /data/install
    chown -R mysql /home/mysql
    chown -R mysql /data/install
    chmod -R a+rwx /data/install
    rm -rf /home/mysql/install
    ln -s /data/install /home/mysql/install
    chown -R mysql /home/mysql/install
    echo "mysql:{{mysql_os_password}}" | chpasswd
    FOUND=$(grep 'ulimit -n' /etc/profile)
    if [ -z "$FOUND" ]; then
            echo 'ulimit -n {{max_open_file}}' >> /etc/profile
    fi
    FOUND=$(grep 'fs.aio-max-nr' /etc/sysctl.conf)
    if [ -z "$FOUND" ];then
        echo "fs.aio-max-nr={{aio_max_nr}}" >> /etc/sysctl.conf
        /sbin/sysctl -p
    fi
    FOUND=$(grep 'export LC_ALL=en_US' /etc/profile)
    if [ -z "$FOUND" ]; then
            echo 'export LC_ALL=en_US' >> /etc/profile
    fi
    FOUND=$(grep 'export PATH=/usr/local/mysql/bin/:$PATH' /etc/profile)
    if [ -z "$FOUND" ]; then
            echo 'export PATH=/usr/local/mysql/bin/:$PATH' >> /etc/profile
    fi
"""  # noqa


class SysInit(BkJobService):
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
        aio_max_nr = 1024000
        max_open_file = 204800
        if kwargs.get("aio_max_nr"):
            aio_max_nr = kwargs["aio_max_nr"]
        if kwargs.get("max_open_file"):
            max_open_file = kwargs["max_open_file"]

        # 如果从从老机器获取max_open_file成功，则使用老实例的值
        try:
            if trans_data is not None:
                max_open_file_old = trans_data.max_open_file
                if isinstance(max_open_file_old, dict):
                    if "sys_max_open_file" in max_open_file_old:
                        max_open_file = max_open_file_old["sys_max_open_file"]
        except Exception:
            pass

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(os_sysctl_init)
        script_content = template.render(
            max_open_file=max_open_file, aio_max_nr=aio_max_nr, mysql_os_password=self._get_os_mysql_password()
        )
        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Init-Mysql-Os",
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
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def _get_os_mysql_password(self):
        """
        获取os_mysql密码
        """
        data = MySQLPrivManagerApi.get_password(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [{"username": UserName.OS_MYSQL.value, "component": MySQLPrivComponent.MYSQL.value}],
            }
        )["items"]
        self.log_info("get os_mysql success")
        return base64.b64decode(data[0]["password"]).decode("utf-8")


class SysInitComponent(Component):
    name = __name__
    code = "sys_init"
    bound_service = SysInit


get_os_sys_param = """
#!/bin/bash 
    sys_max_open_file=`cat /proc/sys/fs/file-max`
    user_max_open_file=`ulimit -n`
    printf "<ctx>{\\\"sys_max_open_file\\\":${sys_max_open_file},\\\"user_max_open_file\\\":${user_max_open_file}}</ctx>"
"""  # noqa


class GetOsSysParam(BkJobService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        script_content = get_os_sys_param
        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Get-Os-Sys-Param",
            "script_content": str(base64.b64encode(script_content.encode("utf-8")), "utf-8"),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER
        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url:{env.BK_JOB_URL}/api_execute/{resp['data']['job_instance_id']}")
        # data.outputs.ext_result = resp
        # result = json.loads(re.search(cpl, resp["data"]["log_content"]).group("context"))
        # setattr(trans_data, "max_open_file", copy.deepcopy(result))
        # data.outputs["trans_data"] = trans_data
        data.inputs.write_payload_var = "max_open_file"
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class GetOsSysParamComponent(Component):
    name = __name__
    code = "get_os_sys_param"
    bound_service = GetOsSysParam

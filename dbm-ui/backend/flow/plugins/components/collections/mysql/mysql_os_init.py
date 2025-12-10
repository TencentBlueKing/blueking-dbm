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

from jinja2.sandbox import SandboxedEnvironment as Environment
from pipeline.component_framework.component import Component

from backend import env
from backend.components import DBPrivManagerApi, JobApi
from backend.db_proxy.reverse_api.common.impl import list_nginx_addrs
from backend.flow.consts import DBA_ROOT_USER, DEFAULT_INSTANCE, MySQLPrivComponent, UserName
from backend.flow.plugins.components.collections.common.base_service import BkJobService
from backend.flow.utils.script_template import fast_execute_script_common_kwargs
from backend.utils.string import base64_encode

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
    # if there is a mysql user an error will be reported in the previous step
    # and home mysql will not be created so make a judgment and create home mysql
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
    mkdir -p /data/install
    chown -R mysql /home/mysql
    chown -R mysql /data/install
    chmod -R a+rwx /data/install
    rm -rf /home/mysql/install
    ln -s /data/install /home/mysql/install
    chown -R mysql /home/mysql/install
    mkdir -p /home/mysql/common_config
    chown -R mysql /home/mysql/common_config
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
                max_open_file_old = trans_data.system_info
                if isinstance(max_open_file_old, dict):
                    if "sys_max_open_file" in max_open_file_old:
                        max_open_file = max_open_file_old["sys_max_open_file"]
        except Exception:
            pass

        nginx_addrs_init = """
        echo '{}' >> /home/mysql/common_config/nginx_proxy.list
        chown mysql /home/mysql/common_config/nginx_proxy.list
        """.format(
            "\n".join(list_nginx_addrs(kwargs["bk_cloud_id"]))
        )

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(os_sysctl_init + nginx_addrs_init)
        script_content = template.render(
            max_open_file=max_open_file, aio_max_nr=aio_max_nr, mysql_os_password=self._get_os_mysql_password()
        )
        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "DBM-Init-Mysql-Os",
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
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True

    def _get_os_mysql_password(self):
        """
        获取os_mysql密码
        """
        data = DBPrivManagerApi.get_password(
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
    glibc_version=$(ldd --version | head -n 1 | awk '{print $NF}')
    if [ -f /etc/os-release ]; then
        version_id=$(grep "^VERSION_ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
        os_id=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
    else
        version_id=""
        os_id=""
    fi
    printf "<ctx>{\\\"sys_max_open_file\\\":${sys_max_open_file},\\\"user_max_open_file\\\":${user_max_open_file},\\\"glibc_version\\\":${glibc_version},\\\"version_id\\\":\\\"${version_id}\\\",\\\"os_id\\\":\\\"${os_id}\\\"}</ctx>"
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
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER
        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")
        # data.outputs.ext_result = resp
        # result = json.loads(re.search(cpl, resp["data"]["log_content"]).group("context"))
        # setattr(trans_data, "max_open_file", copy.deepcopy(result))
        # data.outputs["trans_data"] = trans_data
        data.inputs.write_payload_var = "system_info"
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class GetOsSysParamComponent(Component):
    name = __name__
    code = "get_os_sys_param"
    bound_service = GetOsSysParam


class CleanDataBakDirSvr(BkJobService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        script_content = """
        echo "clean mysqllog bak dir"
        find /data/ -type d -name "mysqllog_2*_bak_*"  -exec rm -rf {} + || true
        find /data/mysqldata/ -mindepth 1 -maxdepth 1 -type d   ! -regex '.*/200[0-9][0-9]$' -exec rm -rf {} + || true
        find /data1/mysqldata/ -mindepth 1 -maxdepth 1 -type d   ! -regex '.*/200[0-9][0-9]$' -exec rm -rf {} + || true
        find /data/dbbak -type f ! \( -name "*.log" -o -name "*.err" \) -delete 2>/dev/null || true
        find /data/dbbak -depth -type d -empty -delete 2>/dev/null || true
        find /data1/dbbak -type f ! \( -name "*.log" -o -name "*.err" \) -delete 2>/dev/null || true
        find /data1/dbbak -depth -type d -empty -delete 2>/dev/null || true
        find /data/dbbak -mindepth 1 -maxdepth 1 -type d -ctime +3 -exec rm -rf {} + 2>/dev/null || true
        find /data1/dbbak -mindepth 1 -maxdepth 1 -type d -ctime +3 -exec rm -rf {} + 2>/dev/null || true
        ps -ef | grep 'db.*exporter' | grep -v grep | awk '{print $2}' | while read PID
        do
            export_install_path=$(pwdx "${PID}" 2>/dev/null | awk '{print $2}')
            kill -9 "${PID}" || true
            sleep 1
            kill -9 "${PID}" || true
            sleep 1
            if [ -n "${export_install_path}" ]; then
                rm -rf "${export_install_path}" || true
            fi
        done
        """  # noqa
        exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs["exec_ip"])
        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "Clean-DataBak-Dir",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER
        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")
        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class CleanDataBakDirComponent(Component):
    name = __name__
    code = "clean_data_bak_dir"
    bound_service = CleanDataBakDirSvr


tlinux4_dependencies_script = """
    echo "install tlinux4 dependencies"
    if [ -f /etc/os-release ]; then
        ID=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"' | xargs)
        ID_LOWER=$(echo "$ID" | tr '[:upper:]' '[:lower:]' | xargs)

        if [ "$ID_LOWER" = "tlinux" ] || [ "$ID_LOWER" = "tencentos" ]; then
            VERSION_ID=$(grep "^VERSION_ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"' | xargs)
            MAJOR_VERSION=$(echo $VERSION_ID | cut -d'.' -f1)

            if [ "$MAJOR_VERSION" -ge 4 ]; then
                echo "OS version check passed: ID=$ID, VERSION_ID=$VERSION_ID"
                mkdir -p /data/install
                if [ -n "{{download_url}}" ] && [ ! -f /data/install/{{pkg}} ]; then
                    cd /data/install/ && wget --header "Host:{{domain}}" --user="{{bk_repo_username}}" --password="{{bk_repo_password}}" --tries=10 {{download_url}} -O {{pkg}}
                    if [ $? -ne 0 ]; then
                        echo "Failed to download {{pkg}}, exit"
                        exit 1
                    fi
                fi
                if [ ! -f /data/install/{{pkg}} ]; then
                    echo "Package file /data/install/{{pkg}} not found, exit"
                    exit 1
                fi
                PKG_NAME=$(rpm -qp --queryformat '%{NAME}' /data/install/{{pkg}} 2>/dev/null)
                if [ -z "$PKG_NAME" ]; then
                    echo "Failed to query package name from {{pkg}}, exit"
                    exit 1
                fi
                if rpm -q "$PKG_NAME" &> /dev/null; then
                    echo "Package $PKG_NAME is already installed, skip installation"
                else
                    echo "Installing package $PKG_NAME..."
                    rpm -ivh /data/install/{{pkg}}
                    if [ $? -ne 0 ]; then
                        echo "Failed to install {{pkg}}, exit"
                        exit 1
                    fi
                fi
                if [ -L /usr/lib64/libmysqlclient.so.21 ]; then
                    echo "Found symlink /usr/lib64/libmysqlclient.so.21, removing it"
                    unlink /usr/lib64/libmysqlclient.so.21
                fi
            else
                echo "Skip installation: ID=$ID, VERSION_ID=$VERSION_ID (requires version 4.x+)"
                exit 0
            fi
        else
            echo "Skip installation: ID=$ID (requires tlinux or tencentos)"
            exit 0
        fi
    else
        echo "Warning: /etc/os-release not found, skip installation"
        exit 0
    fi
"""  # noqa


class AdaptTLinux4DependenciesSvr(BkJobService):
    def __get_exec_ips(self, kwargs, trans_data) -> list:
        """
        获取需要执行的ip list
        """
        # 拼接节点执行ip所需要的信息，ip信息统一用list处理拼接
        if kwargs.get("get_trans_data_ip_var"):
            exec_ips = self.splice_exec_ips_list(pool_ips=getattr(trans_data, kwargs["get_trans_data_ip_var"]))
        else:
            exec_ips = self.splice_exec_ips_list(ticket_ips=kwargs.get("exec_ip"))

        return exec_ips

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")
        pkg = kwargs.get("pkg", "")
        download_url = kwargs.get("download_url", "")
        bk_repo_username = kwargs.get("bk_repo_username", "")
        bk_repo_password = kwargs.get("bk_repo_password", "")

        # 参数校验
        if not pkg:
            self.log_error("pkg parameter is required")
            return False

        if not kwargs.get("exec_ip"):
            self.log_error("exec_ip parameter is required")
            return False

        if not env.BKREPO_ENDPOINT_URL:
            self.log_error("BKREPO_ENDPOINT_URL is not configured")
            return False

        domain = env.BKREPO_ENDPOINT_URL.replace("https://", "").replace("http://", "").rstrip("/")

        # 脚本内容
        jinja_env = Environment()
        template = jinja_env.from_string(tlinux4_dependencies_script)
        script_content = template.render(
            pkg=pkg,
            download_url=download_url,
            domain=domain,
            bk_repo_username=bk_repo_username,
            bk_repo_password=bk_repo_password,
        )

        exec_ips = self.__get_exec_ips(kwargs=kwargs, trans_data=trans_data)
        if not exec_ips:
            self.log_error("No execution IPs found")
            return False

        target_ip_info = [{"bk_cloud_id": kwargs["bk_cloud_id"], "ip": ip} for ip in exec_ips]
        body = {
            "bk_biz_id": env.JOB_BLUEKING_BIZ_ID,
            "task_name": "Adapt-TLinux4-Dependencies",
            "script_content": base64_encode(script_content),
            "script_language": 1,
            "target_server": {"ip_list": target_ip_info},
        }
        self.log_info("ready start task with body {}".format(body))

        common_kwargs = copy.deepcopy(fast_execute_script_common_kwargs)
        common_kwargs["account_alias"] = DBA_ROOT_USER
        resp = JobApi.fast_execute_script({**common_kwargs, **body}, raw=True)
        self.log_info(f"fast execute script response: {resp}")

        # 检查响应结果
        if not resp.get("result") or not resp.get("data") or not resp["data"].get("job_instance_id"):
            self.log_error(f"Failed to execute script: {resp}")
            return False

        self.log_info(f"job url: {self.__url__(resp['data']['job_instance_id'])}")
        data.outputs.ext_result = resp
        data.outputs.exec_ips = exec_ips
        return True


class AdaptTLinux4DependenciesComponent(Component):
    name = __name__
    code = "adapt_tlinux4_dependencies"
    bound_service = AdaptTLinux4DependenciesSvr

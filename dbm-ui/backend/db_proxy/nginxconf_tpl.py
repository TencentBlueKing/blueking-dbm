"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from jinja2 import Environment, Template

from backend.db_proxy.models import ClusterExtension
from backend.utils.string import base64_encode


def render_nginx_tpl(extension: ClusterExtension, template: Template = None, conf_tpl: str = None, encode=True):
    """渲染nginx子配置模板文件"""
    if not template:
        jinja_env = Environment()
        template = jinja_env.from_string(conf_tpl)

    conf_payload = {
        "bk_biz_id": extension.bk_biz_id,
        "bk_cloud_id": extension.bk_cloud_id,
        "db_type": extension.db_type,
        "cluster_name": extension.cluster_name,
        "service_type": extension.service_type,
        "service_url": f"http://{extension.ip}:{extension.port}",
    }
    file_name = f"{extension.bk_biz_id}_{extension.db_type}_{extension.cluster_name}_nginx.conf"
    file_content = template.render(conf_payload)

    if encode:
        file_content = base64_encode(file_content)

    return {"file_name": file_name, "content": file_content}


es_conf_tpl = """
location /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}} {
    rewrite /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/(.*) /$1 break;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass {{service_url}};
    client_max_body_size 100m;
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    proxy_buffer_size 4k;
    proxy_buffers 32 4k;
    proxy_busy_buffers_size 64k;
}
"""

doris_conf_tpl = """
location /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}} {
    rewrite /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/(.*) /$1 break;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass {{service_url}};
    client_max_body_size 100m;
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    proxy_buffer_size 4k;
    proxy_buffers 32 4k;
    proxy_busy_buffers_size 64k;
}
"""

hdfs_conf_tpl = """
location /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}} {
    rewrite /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/(.*) /$1 break;
    sub_filter 'src="/' 'src="/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/';
    sub_filter 'href="/' 'href="/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/';
    sub_filter '/jmx?' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/jmx?';
    sub_filter '/startupProgress' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/startupProgress';
    sub_filter '/webhdfs/v1' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/webhdfs/v1';
    sub_filter_types *;
    sub_filter_once  off;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass {{service_url}};
    client_max_body_size 100m;
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    proxy_buffer_size 4k;
    proxy_buffers 32 4k;
    proxy_busy_buffers_size 64k;
}
"""

kafka_conf_tpl = """
location /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}} {
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass {{service_url}}/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}};
    client_max_body_size 100m;
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    proxy_buffer_size 4k;
    proxy_buffers 32 4k;
    proxy_busy_buffers_size 64k;
}
"""

pulsar_conf_tpl = """
location /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}} {
    rewrite /{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/(.*) /$1 break;
    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_pass {{service_url}}/ui/index.html;
    client_max_body_size 100m;
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    proxy_buffer_size 4k;
    proxy_buffers 32 4k;
    proxy_busy_buffers_size 64k;
    sub_filter '/pulsar-manager' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/pulsar-manager';
    sub_filter '"/admin/' '"/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/admin/';
    sub_filter '/lookup' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/lookup';
    sub_filter '/bkvm' '/{{bk_biz_id}}/{{db_type}}/{{cluster_name}}/{{service_type}}/bkvm';
    sub_filter_types *;
    sub_filter_once  off;
}
"""

restart_nginx_tpl = """
cd /usr/local/bkdb/nginx-portable
./nginx-portable stop
./nginx-portable start
"""

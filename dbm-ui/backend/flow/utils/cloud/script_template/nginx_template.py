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
# 启用nginx服务的部署脚本
start_nginx_template = """
path=/usr/local/bkdb
mkdir -p $path

# 卸载旧版nginx，重新安装nginx
$path/nginx-portable/nginx-portable stop || :;
rm -rf $path/nginx-portable/;
tar xvf /data/install/nginx-portable.tgz -C $path;
chmod -R 755 $path/nginx-portable/;
user=root;
group=root;

# 将证书文件放置制定目录
mkdir -p /etc/nginx/
mv /data/install/*.crt /data/install/*.key /etc/nginx

# 创建用户和组
egrep "^$group" /etc/group >& /dev/null;
if [ $? -ne 0 ]; then
    groupadd $group;
fi

egrep "^$user" /etc/passwd >& /dev/null;
if [ $? -ne 0 ]; then
    useradd -g $group $user;
fi

DNS_LIST=$(awk 'BEGIN{ORS=" "} $1=="nameserver" {print $2}' /etc/resolv.conf)
if ! grep -q "nameserver.*127.0.0.1" /etc/resolv.conf; then
    DNS_LIST+=(127.0.0.1);
fi
echo -e "
user $user;
events {
    worker_connections  65535;
}
http {
    # 基础配置
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;

    # 设置日志
   #  log_format  main
   # ' $remote_user [$time_local]  $http_x_Forwarded_for $remote_addr  $request '
   # '$http_x_forwarded_for '
   # '$upstream_addr '
   # 'ups_resp_time: $upstream_response_time '
   # 'request_time: $request_time';

    upstream drs_server{
        {{upstream_drs_server}}
        ip_hash;
    }

    # 转发drs服务
    server {
        listen 443 ssl;
        server_name {{nginx_external_domain}};
        resolver ${DNS_LIST[@]};

        ssl_certificate /etc/nginx/server.crt;
        ssl_certificate_key /etc/nginx/server.key;
        ssl_verify_client on;
        ssl_client_certificate /etc/nginx/server.crt;
        ssl_session_cache shared:SSL:1m;
        ssl_session_timeout  10m;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        proxy_connect;
        proxy_connect_allow 443 563;
        location / {
            proxy_ssl_certificate /etc/nginx/client.crt;
            proxy_ssl_certificate_key /etc/nginx/client.key;
            proxy_pass https://drs_server/$request_uri;
            proxy_connect_timeout 10s;
        }
    }

    # 转发大数据组件服务
    server {
        listen {{manage_port}};
        server_name {{nginx_external_domain}};
        resolver ${DNS_LIST[@]};
        proxy_connect;
        proxy_connect_allow 443 563;

        # 包含到大数据服务的子配置
        include /usr/local/bkdb/nginx-portable/conf/cluster_service/*.conf;

    }

    # 转发dbm的透传服务
    server {
        listen {{dbm_port}};
        server_name {{nginx_internal_domain}};
        resolver ${DNS_LIST[@]};
        proxy_connect;
        proxy_connect_allow 443 563;

        location /apis/proxypass/ {
            # 重写上传接口的uri
            rewrite /generic/(.*)/(.*)/(.*)/  /apis/proxypass/generic/\$1/\$2/\$3/ break;

            # 注意如果dbm_momain是以https开头的，则需要配置SSL
            proxy_pass {{dbm_momain}};
        }
    }

}" > $path/nginx-portable/conf/nginx.conf;

# 开启nginx服务
touch $path/nginx-portable/logs/nginx.pid
$path/nginx-portable/nginx-portable start;
sleep 5;

# 探测端口是否监听
is_port_listen_by_pid () {
    echo $@;
    for port in "$@"; do
        local pid=$(lsof -i:$port | awk '{print $2}' | tail -n 1);
        if [[ $pid == "" ]]; then
            echo "Nginx service deployment has failed, error port: $port";
            return 1;
        fi
    done
    echo "Nginx service start successfully";
}
echo "nginx-pid: $(cat $path/nginx-portable/logs/nginx.pid)";
is_port_listen_by_pid 80;
exit $?
"""

nginx_stop_template = """
path=/usr/local/bkdb
$path/nginx-portable/nginx-portable stop;
rm -rf $path/nginx-portable/
"""

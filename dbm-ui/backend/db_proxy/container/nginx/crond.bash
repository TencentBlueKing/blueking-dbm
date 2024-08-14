#!/bin/bash
path=/usr/local/bkdb

# nginx定时拉取大数据配置，这里只考虑直连区域
data=$(
curl -XPOST "$BK_DBM_URL/apis/proxypass/cloud/pull_nginx_conf/" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "bk_cloud_id": 0,
    "extension": "NGINX",
    "db_cloud_token": "'"$DB_CLOUD_TOKEN"'",
    "details": {
      "ip": "'"$DBM_NGINX_DOMAIN"'",
      "bk_host_id": 0,
      "bk_cloud_id": 0
    }
  }'
)
echo "$data" | jq -c '.data[]' | while read -r item; do
    file_name=$(echo "$item" | jq -r '.file_name')
    file_content=$(echo "$item" | jq -r '.content')
    # 创建文件并写入内容
    echo "$file_content" > "$path/nginx-portable/conf/cluster_service/$file_name"
done
# 重启nginx
$path/nginx-portable/nginx-portable stop
$path/nginx-portable/nginx-portable start

# nginx日志文件的定时清理，设置最大日志为100MB
nginx_log_path="$path/nginx-portable/logs"
max_log_size=$((100 * 1024 * 1024))
access_log_size=$(stat -c%s "$path/nginx-portable/logs/access.log")
if [ "$access_log_size" -gt "$max_log_size" ]; then
    echo > $nginx_log_path/access.log;
fi
err_log_size=$(stat -c%s "$path/nginx-portable/logs/error.log")
if [ "$err_log_size" -gt "$max_log_size" ]; then
    echo > $nginx_log_path/err_log_size.log;
fi

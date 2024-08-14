path=/usr/local/bkdb
mkdir -p $path

# 写入nginx记录
curl -XPOST "$BK_DBM_URL/apis/proxypass/cloud/insert/" \
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

# 解压nginx
tar xvf /data/install/nginx-portable.tgz -C $path;
chmod -R 755 $path/nginx-portable/;
mkdir -p $path/nginx-portable/conf/cluster_service/

envsubst < /data/install/nginx-tpl.conf > /data/install/nginx.conf
mv /data/install/nginx.conf /data/install/crond.bash $path/nginx-portable/conf/

# 注入测试location
mkdir $path/nginx-portable/html/example_service/
mv /data/install/dbm.html $path/nginx-portable/html/example_service/
echo -e "
location /example_service/ {
    root $path/nginx-portable/html;
    index dbm.html;
}
" > $path/nginx-portable/conf/cluster_service/example_service.conf

# 开启定时任务
printenv > /etc/environment
crond_script_path=$path/nginx-portable/conf/crond.bash
(crontab -l ; echo "*/5 * * * * $crond_script_path") 2>&1 | grep -v "no crontab" | sort | uniq | crontab -

# 开启nginx服务
$path/nginx-portable/nginx-portable start;
tail -f $path/nginx-portable/logs/access.log

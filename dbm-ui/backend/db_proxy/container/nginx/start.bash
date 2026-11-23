path=/usr/local/bkdb
mkdir -p $path

# 开启 KMS 时用信封中的 app_code / app_secret 覆盖 ConfigMap 中的 DB_CLOUD_TOKEN，明文只保留在进程环境变量中
if [ "$ENABLE_KMS" = "true" ]; then
    app_code=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_code) || exit 1
    app_secret=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_secret) || exit 1
    export DB_CLOUD_TOKEN="${app_code}:${app_secret}"
    unset app_code app_secret BK_DBM_KMS_PRIVATE_KEY
fi

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
      "bk_cloud_id": 0,
      "dbm_port": 80
    }
  }'

# 解压nginx
tar xvf /data/install/nginx-portable.tgz -C $path;
chmod -R 755 $path/nginx-portable/;
mkdir -p $path/nginx-portable/conf/cluster_service/

envsubst '${DBM_NGINX_DOMAIN} ${BK_DBM_URL}' < /data/install/nginx-tpl.conf > /data/install/nginx.conf
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

# 开启定时任务：用后台循环代替 cron，直接继承环境变量，避免把 DB_CLOUD_TOKEN 写入 /etc/environment
crond_script_path=$path/nginx-portable/conf/crond.bash
(while true; do sleep 300; "$crond_script_path" > /dev/null 2>&1; done) &

# 开启nginx服务
$path/nginx-portable/nginx-portable start;
tail -f $path/nginx-portable/logs/access.log

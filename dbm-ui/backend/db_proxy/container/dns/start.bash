path=/usr/local;

# 开启 KMS 时用信封中的 app_code / app_secret 覆盖 ConfigMap 中的 DB_CLOUD_TOKEN，明文只保留在进程环境变量中
if [ "$ENABLE_KMS" = "true" ]; then
    app_code=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_code) || exit 1
    app_secret=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_secret) || exit 1
    export DB_CLOUD_TOKEN="${app_code}:${app_secret}"
    unset app_code app_secret BK_DBM_KMS_PRIVATE_KEY
fi

# 写入dns记录
data=$(
curl -XPOST "$BK_DBM_URL/apis/proxypass/cloud/insert/" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "bk_cloud_id": 0,
    "extension": "DNS",
    "db_cloud_token": "'"$DB_CLOUD_TOKEN"'",
    "details": {
      "ip": "'"$NODE_IP"'",
      "bk_city": "",
      "is_access": 1,
      "bk_host_id": 0,
      "bk_cloud_id": 0
    }
  }'
)

# 导出监控环境变量
export BKMONITOR_EVENT_DATA_ID=$(echo $data | jq -r '.data.bkm_dbm_report.event.data_id')
export BKMONITOR_EVENT_TOKEN=$(echo $data | jq -r '.data.bkm_dbm_report.event.token')

# 解压bind文件
tar -xvf /data/install/bind.tar.gz -C $path;
ln -s $path/bind9 $path/bind;
# 启动bind服务
chown -R root:root $path/bind/*
$path/bind/sbin/named -4

# 配置pull-crond服务的文件路径
mv /data/install/pull-crond $path/bind/admin;
mv /data/install/pull-crond.conf $path/bind/admin;

# 增加定时拉起命令
crontab -l > crontab_backup.txt
command="* * * * * cd $path/bind/admin; /bin/sh check_dns_and_pull_crond.sh 1>/dev/null 2>&1"

if crontab -l | grep -Fxq "$command"; then
    echo "Scheduled pull task already exists, ignore..."
else
    (crontab -l ; echo "$command") | uniq - | crontab -
    echo "Pull up task has been added to crontab。"
fi

# 启动pull-crond服务
cd $path/bind/admin/;
chmod 777 pull-crond;
# 渲染后的配置含 token，写到 helm 挂载的内存盘 /data/secure；原路径保留软链，兼容 crontab 保活脚本
mkdir -p /data/secure
envsubst < pull-crond.conf > /data/secure/pull-crond-run.conf
ln -sf /data/secure/pull-crond-run.conf pull-crond-run.conf
./pull-crond -c pull-crond-run.conf;

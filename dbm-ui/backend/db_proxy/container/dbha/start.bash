# 开启 KMS 时用信封中的 app_code / app_secret 覆盖 ConfigMap 中的 DB_CLOUD_TOKEN，明文只保留在进程环境变量中
if [ "$ENABLE_KMS" = "true" ]; then
    app_code=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_code) || exit 1
    app_secret=$(/data/install/bk-dbm-kms get bkapp_id_secret.default.app_secret) || exit 1
    export DB_CLOUD_TOKEN="${app_code}:${app_secret}"
    unset app_code app_secret BK_DBM_KMS_PRIVATE_KEY
fi

# 写入dbha记录
# city_id: -1 表示探测所有实例
data=$(
curl -XPOST "$BK_DBM_URL/apis/proxypass/cloud/insert/" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "bk_cloud_id": 0,
    "extension": "DBHA",
    "db_cloud_token": "'"$DB_CLOUD_TOKEN"'",
    "details": {
      "ip": "%",
      "dbha_type": "'"$DBHA_TYPE"'",
      "bk_city_code": "'"$DBHA_CITY"'",
      "bk_city_name": "'"$DBHA_CAMPUS"'",
      "bk_host_id": 0,
      "bk_cloud_id": 0
    }
  }'
)

# 导出密码环境变量
export DBHA_USER=$(echo $data | jq -r '.data.dbha_account.user')
export DBHA_PASSWORD=$(echo $data | jq -r '.data.dbha_account.password')
export DBHA_PROXY_PASSWORD=$(echo $data | jq -r '.data.proxy_password')
export MYSQL_OS_PASSWORD=$(echo $data | jq -r '.data.mysql_os_password')
# DBHA ssh端口：优先环境变量，否则默认36000
export DBHA_SSH_PORT=${DBHA_SSH_PORT:-36000}
export SQLSERVER_OS_USER=$(echo $data | jq -r '.data.sqlserver_os_user')
export SQLSERVER_OS_PASSWORD=$(echo $data | jq -r '.data.sqlserver_os_password')
# 导出监控环境变量
export BKMONITOR_EVENT_DATA_ID=$(echo $data | jq -r '.data.bkm_dbm_report.event.data_id')
export BKMONITOR_EVENT_TOKEN=$(echo $data | jq -r '.data.bkm_dbm_report.event.token')

# 配置文件注入环境变量，启动dbha服务
# 渲染后的配置含 token 和密码，写到 helm 挂载的内存盘 /data/secure，不落磁盘
mkdir logs && touch logs/log
mkdir -p /data/secure
envsubst < ./dbha-conf-tpl.yaml > /data/secure/dbha.conf
nohup ./dbha -config_file=/data/secure/dbha.conf -type=$DBHA_TYPE -> dbha-apply.log 2>&1 &
tail -f logs/log

# 写入dbha记录
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
# 导出监控环境变量
export BKMONITOR_EVENT_DATA_ID=$(echo $data | jq -r '.data.bkm_dbm_report.event.data_id')
export BKMONITOR_EVENT_TOKEN=$(echo $data | jq -r '.data.bkm_dbm_report.event.token')

# 配置文件注入环境变量，启动dbha服务
touch log
envsubst < ./dbha-conf-tpl.yaml > ./dbha.conf
nohup ./dbha -config_file=dbha.conf -type=$DBHA_TYPE -> dbha-apply.log 2>&1 &
tail -f log

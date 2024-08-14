# 写入DRS记录
data=$(
curl -XPOST "$BK_DBM_URL/apis/proxypass/cloud/insert/" \
  --header "Content-Type: application/json" \
  --data-raw '{
    "bk_cloud_id": 0,
    "extension": "DRS",
    "db_cloud_token": "'"$DB_CLOUD_TOKEN"'",
    "details": {
      "ip": "%",
      "bk_host_id": 0,
      "bk_cloud_id": 0
    }
  }'
)

# 导出环境变量
export DRS_MYSQL_ADMIN_PASSWORD=$(echo $data | jq -r '.data.drs_account.password')
export DRS_MYSQL_ADMIN_USER=$(echo $data | jq -r '.data.drs_account.user')
export SQLSERVER_ADMIN_PASSWORD=$DRS_MYSQL_ADMIN_PASSWORD
export SQLSERVER_ADMIN_USER=$DRS_MYSQL_ADMIN_USER
export DRS_PROXY_ADMIN_USER="proxy"
export DRS_PROXY_ADMIN_PASSWORD=$(echo $data |  jq -r '.data.proxy_password')
export DRS_WEBCONSOLE_USER=$(echo $data | jq -r '.data.webconsole_account.user')
export DRS_WEBCONSOLE_PASSWORD=$(echo $data | jq -r '.data.webconsole_account.password')

# 将dns ip添加到nameserver
awk -F, '{for(i=1; i<=NF; i++) print "nameserver " $i}' shard_env/dns_ip > dns_nameserver.conf
cp /etc/resolv.conf /etc/resolv.conf.bak
cat dns_nameserver.conf /etc/resolv.conf.bak > /etc/resolv.conf

# 启动drs
./db-remote-service

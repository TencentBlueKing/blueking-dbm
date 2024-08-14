path=/usr/local;

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
envsubst < pull-crond.conf > pull-crond-run.conf
./pull-crond -c pull-crond-run.conf;

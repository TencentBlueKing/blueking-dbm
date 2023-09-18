
## dump schema:
```
/usr/local/mysql/bin/mysqldump --default-character-set=utf8 \
 --skip-opt --quick --create-options --no-create-db --no-data \
 --socket /data1/mysqldata/20000/mysql.sock --port=20000 \
 bk_dbconfig > 000002_create_table.up.sql

sed -i '/DEFINER=/d' 000002_create_table.up.sql
sed -i 's/CREATE TABLE /CREATE TABLE IF NOT EXISTS /g' 000002_create_table.up.sql
```

## dump data:
按不同的 namespace 生成初始化 migrate 数据，比如 tendbha:
```
dbuser=xx
dbpass=xxx
seqno=10
namespaces="common es hdfs kafka PredixyTendisplusCluster rediscomm RedisInstance RedisMS tendb tendbcluster tendbha tendbsingle TendisCache TendisplusInstance TendisSSD TendisX TwemproxyRedisInstance TwemproxyTendisplusInstance TwemproxyTendisSSDInstance pulsar influxdb riak"
dbname=dbconfig_release
exclude_sensitive="(flag_encrypt!=1 or value_default like '{{%')"

for namespace in $namespaces
do
  mig_id="0000${seqno}"
  echo "${mig_id}_${namespace}_data"
  dumpcmd="/usr/local/mysql/bin/mysqldump --default-character-set=utf8  --skip-opt --quick --no-create-db --no-create-info --complete-insert  --socket /data1/mysqldata/20000/mysql.sock --port=20000 -u$dbuser -p$dbpass"
  $dumpcmd $dbname tb_config_file_def --where="namespace='${namespace}'" > ${mig_id}_${namespace}_data.up.sql
  $dumpcmd $dbname tb_config_name_def --where="namespace='${namespace}' AND ${exclude_sensitive}" >> ${mig_id}_${namespace}_data.up.sql
 
  echo "DELETE FROM tb_config_file_def WHERE namespace='${namespace}';
DELETE FROM tb_config_name_def WHERE namespace='${namespace}' AND ${exclude_sensitive};" > ${mig_id}_${namespace}_data.down.sql
 
 let seqno+=1
done
sed -i '/Dump completed on /d' 0000*.sql
```

migrates 文件名前缀一次保持递增
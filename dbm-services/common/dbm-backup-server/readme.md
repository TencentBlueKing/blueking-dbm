
## backup-server 多环境相关数据迁移
原 db 全量导出：
```
DBAUTH="-uxxx -pxxx -h1.2.3.4 -P3306"  # db连接信息
DBNAME="bk_dbm_backup_server"

mysqldump $DBAUTH --default-character-set=utf8mb4 \
  --hex-blob --skip-opt --skip-lock-tables --skip-add-locks \
  --extended-insert=false -n -t \
  --replace -q --set-gtid-purged=OFF \
  $DBNAME tb_bucket tb_bucket_route > dbbackupserver_biz_data_full.sql
  
-- 是否要迁移历史 tb_backup_tasklist 记录表，取决于需求。可默认不迁移
```

新 db 全量导入
```
DBAUTH_NEW=""  # 新 db 的连接信息
DBNAME_NEW=""  # 导入到新的 db 名，取决于租户配置

mysql $DBAUTH_NEW $DBNAME_NEW < dbbackupserver_biz_data_full.sql
```
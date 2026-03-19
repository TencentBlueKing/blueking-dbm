
## dbconfig 的环境相关数据迁移
tb_config_file_def, tb_config_name_def 由系统初始化数据，不要迁移

需要迁移的是业务/集群的个性化配置，涉及以下 2 个表数据导出和导入
tb_config_node
tb_config_versioned 


## 导出

1. 先全量导出导入，避免后续自增 id冲突
2. 后续如果原平台/原 db，有在全量导出后，新增 db 集群，对该业务重新导出导入

### 全量导出导入

原 db 全量导出：
```
DBAUTH="-uxxx -pxxx -h1.2.3.4 -P3306"  # db连接信息
DBNAME="bk_dbconfig"

mysqldump $DBAUTH --default-character-set=utf8mb4 \
  --hex-blob --skip-opt --skip-lock-tables --skip-add-locks \
  --extended-insert=false -n -t \
  $DBNAME tb_config_node tb_config_versioned > dbconfig_biz_data_full.sql
```

新 db 全量导入
```
DBAUTH_NEW=""  # 新 db 的连接信息
DBNAME_NEW=""  # 导入到新的 db 名，取决于租户配置

mysql $DBAUTH_NEW $DBNAME_NEW < dbconfig_biz_data_full.sql
```

### 对某个业务单独导出导入

可以重复执行，面对有增量的情况

按业务导出:
```
DBAUTH="-uxxx -pxxx -h1.2.3.4 -P3306"  # db连接信息
DBNAME="bk_dbconfig"
BK_BIZ_ID=1234  # 要迁移的 bk_biz_id

mysqldump $DBAUTH --default-character-set=utf8mb4 \
  --hex-blob --skip-opt --skip-lock-tables --skip-add-locks \
  --extended-insert=false -n -t \
  --replace --where="bk_biz_id='${BK_BIZ_ID}'" \
  $DBNAME tb_config_node tb_config_versioned > dbconfig_biz_data_${BK_BIZ_ID}.sql
```

按业务导入:
```
DBAUTH_NEW=""  # 新 db 的连接信息
DBNAME_NEW=""  # 导入到新的 db 名，取决于租户配置
BK_BIZ_ID=1234  # 要迁移的 bk_biz_id

mysql $DBAUTH $DBNAME < dbconfig_biz_data_${BK_BIZ_ID}.sql
```
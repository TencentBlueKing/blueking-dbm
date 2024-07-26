
## dbbackup dumplogical

逻辑备份专用命令，一般用于非例行备份的数据导出、迁移

### 功能
1. mydumper 无法在 glibc < 2.14(centos 6.x) 上运行，默认会自动根据操作系统版本，选择是否用传统的 mysqldump
2. `--use-mysqldump = yes` 也可以强制使用 mysqldump 导出 

```
./dbbackup dumpbackup logical --help
logical dump using mydumper or mysqldump

Usage:
  dbbackup dumpbackup logical [flags]

Flags:
  -c, --config string              config file to backup, other options will overwrite this config file temporary
  -B, --databases string           Database to dump, default all
  -E, --events                     Dump stored procedures and functions. By default, it do not dump stored procedures nor functions
      --exclude-databases string   databases to dump, comma separated, default empty
      --exclude-tables string      tables to dump, comma separated, default empty
  -d, --no-data                    tables to dump, comma separated
  -m, --no-schemas                 Do not dump table data
  -x, --regex string               Regular expression for 'db.table' matching
  -R, --routines                   Dump events. By default, it do not dump events
      --tables string              tables to dump, comma separated, default all
  -T, --tables-list string         Comma delimited table list to dump (does not exclude regex option). Table name must include database name. For instance: test.t1,test.t2
      --threads int                threads for mydumper (default 4)
  -G, --triggers                   Dump triggers. By default, it do not dump triggers
      --use-mysqldump string       no, yes, auto, overwrite LogicalBackup.UseMysqldump

Global Flags:
      --backup-client              enable backup-client, overwrite BackupClient.Enable
      --backup-dir string          backup root path to save, overwrite Public.BackupDir (default "/data/dbbak")
      --backup-file-tag string     overwrite BackupClient.FileTag
      --backup-id string           overwrite Public.BackupId
      --bill-id string             overwrite Public.BillId
      --cluster-domain string      cluster domain to report, overwrite Public.ClusterAddress
      --data-schema-grant string   all|schema|data|grant, overwrite Public.DataSchemaGrant
      --help                       help for this command
  -h, --host string                The host to connect to, overwrite Public.MysqlHost
      --nocheck-diskspace          overwrite Public.NoCheckDiskSpace
  -p, --password string            User password, overwrite Public.MysqlPasswd
  -P, --port int                   TCP/IP port to connect to, overwrite Public.MysqlPort (default 3306)
      --shard-value int            overwrite Public.ShardValue (default -1)
  -u, --user string                Username with the necessary privileges, overwrite Public.MysqlUser
```

### 参数说明
- `--config`
  指定 dbbackup.xxx.ini 配置文件，主要用于读取一些默认参数，比如限速、cluster_id 等信息。
  也可不指定，完全使用命令行生成配置
- `--backup-client`
  启用备份上报到备份系统
- `--backup-dir`
  备份目录，目录必须存在
- `--cluster-domain`
  备份集群的标签

**备份对象：**
通过两种形式决定
- `--data-schema-grant`
  简单形式：`all`, `schema`, `data`
- `--no-data`, `--no-schemas`, `--triggers`, `--routines`, `--events`
  复杂形式

**备份库表过滤：**
可用三种形式的过滤器，其中 1 优先级最高
1. `--databases`, `--tables`, `--exclude-databases`, `--exclude-tables`
  精确库名表名，mydumper 与 mysqldump 都兼容的选项。使用示例
  - 备份指定库: `--databases db1,db2`
  - 备份指定库表: `--databases db1 --tables table1,table2`
  - 忽略指定库: `--exclude-databases db2,db3`
2. `--tables-list`
  精确库表名，格式必须是 db1.table1 这样，`,` 号分割。例如 `--tables-list db1.table1 db2.table2`
  建议 mydumper 使用
3. `--regex`
  mydumper 专属过滤方式

### 示例
```
# 导出 db1,db2 两个库的表结构
./dbbackup dumpbackup logical -h x.x.x.x -u x -p y -P 3306 \
 --data-schema-grant=schema \
 --backup-dir /data/dbbak \
 --cluster-domain=xx.xx \
 --databases db1,db2

# 导出 db1 库中 table1,table2 的表结构和数据
./dbbackup dumpbackup logical -h x.x.x.x -u x -p y -P 3306 \
 --data-schema-grant=all \
 --backup-dir /data/dbbak \
 --cluster-domain=xx.xx \
 --databases db1 --tables table1,table2
```

成功后会输出:
```
backup_index_file:/data/dbbak/0_0_x.x.x.x_3306_20240724161133_logical.index
```
备份文件信息则在对应的目录下
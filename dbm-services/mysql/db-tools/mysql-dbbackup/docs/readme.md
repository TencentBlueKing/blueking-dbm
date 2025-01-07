# 1. dbbackup-go
使用go语言编写，可对mysql执行逻辑备份和物理备份。物理备份目前仅适用Mysql的innodb存储引擎

## 目录结构

# 2. 执行方法
dbbackup支持的option：
```
./dbbackup -h
Usage:
  dbbackup [command]

Available Commands:
  completion  Generate the autocompletion script for the specified shell
  dumpbackup  run backup
  help        Help about any command
  loadbackup  run load backup

Flags:
  -c, --config string   config file
  -h, --help            help for dbbackup
  -v, --version         version for dbbackup
```
* 生成备份：
./dbbackup --configpath=/../../..  --dumpbackup
* 导入备份：
./dbbackup --configpath=/../../..  --loadbackup

# 3. 配置文件和备份行为
## 3.1 dumpbackup
生成备份时，即 `dumpbackup`，其配置文件config的格式为ini，配置项如下：
```
[Public]
MysqlHost       =       x.x.x.x
MysqlPort       =       3306
MysqlUser       =       xx
MysqlPasswd     =       xx
MysqlCharset    =
MysqlRole       =       slave
BackupType      =       physical  # physical | logical | auto
DataSchemaGrant =       grant
NoCheckDiskSpace        =       false
OldFileLeftDay  =       2
BkBizId =       123
BkCloudId       =       0
ClusterId       =       1234
ClusterAddress  =       xx.xx.xx.db
ShardValue      =       0
BackupTimeout   =       09:00:00
BackupDir       =       /data/dbbak/
IOLimitMBPerSec =       300
IOLimitMasterFactor     =       0.5
TarSizeThreshold        =       8192
FtwrlWaitTimeout        =       120
AcquireLockWaitTimeout  =       10
KillLongQueryTime       =       0
BillId  =
BackupId        =
ReportPath      =       /home/mysql/dbareport/mysql/dbbackup
StatusReportPath        =       /home/mysql/dbareport/mysql/dbbackup/status

[PhysicalBackup]
Threads =       2
Throttle        =       200
DefaultsFile    =       /etc/my.cnf
DisableSlaveMultiThread =       true
MaxMyisamTables =       10
ExtraOpt        =

[LogicalBackup]
Regex   =       ^(?=(?:(.*\..*$)))(?!(?:(test\..*$|mysql\..*$|sys\..*$|db_infobase\..*$|information_schema\..*$|performance_schema\..*$)))
Databases       =       *
Tables  =       *
ExcludeDatabases        =       # 默认会排除这些系统库 mysql,sys,test,information_schema,performance_schema,db_infobase
ChunkFilesize   =       2048
DisableCompress =       false
Threads =       4
FlushRetryCount =       3
TrxConsistencyOnly      =       true
DefaultsFile    =
ExtraOpt        =
UseMysqldump    =       no  # auto | no | yes

[LogicalBackupMysqldump]
BinPath =
ExtraOpt        =

[EncryptOpt]
EncryptElgo     =
EncryptPublicKey        =
EncryptCmd      =       openssl
EncryptEnable   =       false

[BackupClient]
FileTag =       MYSQL_FULL_BACKUP
StorageType     =
DoChecksum      =       true
Enable  =       true
```
OldFileLeftDay  = N  ： dbbackup运行时，首先删除距今N天的备份文件。如果发现硬盘空间不足，则删除所有以前的备份文件。

TarSizeThreshold (bytes)： 每个tar包的大小不超过TarSizeThreshold值。
### logicalbackup
dbbackup调用mydumper生成逻辑备份文件(sql文件)，若一个库表对应的sql文件过大，可由Part_MaxRows和 Part_ChunkSize控制切分sql文件大小。然后对所有的逻辑备份文件按词典序排列，将多个逻辑备份文件打包到一个tar包。若逻辑备份文件累计大小超过TarSizeThreshold，则打包到一个新的tar包，以此类推。

关于逻辑备份文件的拆分规则，PartMaxRows和 PartChunkSize。先按行数PartMaxRows拆分，拆分后再按文件大小 PartChunkSize拆分

### physicalbackup
dbbackup备份后的文件会打包到一个tar包，并按TarSizeThreshold大小进行拆分，拆分的速度由SplitSpeed 控制，限速单位为MB/s。

## 3.2 loadbackup
导入备份时，即 `loadbackup`，其配置文件config的格式为ini，配置项如下：

### logicalload
IndexFilePath是必输入项，取值为index文件的路径
```
[LogicalLoad]
  MysqlHost             string `ini:"MysqlHost"`
  MysqlPort             string `ini:"MysqlPort"`
  MysqlUser             string `ini:"MysqlUser"`
  MysqlPasswd           string `ini:"MysqlPasswd"`
  MysqlCharset          string `ini:"MysqlCharset"`
  MysqlLoadDir          string `ini:"MysqlLoadDir"`
  Regex                 string `ini:"Regex"`
  Threads               int    `ini:"Threads"`
  RecordBinlog          bool   `ini:"RecordBinlog"`    //恢复数据时，mysql是否要生成binlog
  IndexFilePath         string `ini:"IndexFilePath"`   //必要的配置项，输入index文件的路径
  MyloaderDefaultsFile string `ini:"MydumperDefaultsFile"` //暂未启用
 ```
 
### physicalload
 IndexFilePath是必输入项，取值为index文件的路径
 
 copyback代表恢复目录时，是采用copy还是move操作
 ```
[PhysicalLoad]
  MysqlLoadDir      string `ini:"MysqlLoadDir"`
  Threads           int    `ini:"Threads"`
  CopyBack          bool   `ini:"CopyBack"`
  IndexFilePath     string `ini:"IndexFilePath"` //必要配置项
  MysqlDefaultsFile string `ini:"MysqlDefaultsFile"`
  ...
```

MysqlLoadDir 是指要导入的备份目录(具体指备份tar包解压后的目录)

CopyBack 传true，是指导入备份到实例后，保留备份目录。传false，类似linux mv命令行为，可以理解为导入备份到实例后，删除备份目录。


## 3.3 生成备份
dbbabckup 执行 dumpbackup 后，会生成以下数据：
```
* .priv文件   记录mysql的权限信息

* .tar文件  记录mysql的逻辑备份数据

* .index文件  记录库表与tar文件的映射信息
```
### 逻辑备份
逻辑备份文件，备份一个表有三个文件，
以test.t1为例
```
test.t1.00000.sql.zst   //记录sql语句

test.t1-metadata  //记录test.t1有多少行记录

test.t1-schema.sql.zst //记录test.t1的表结构
```

上述备份文件都打包在\* \.tar文件

\* \.tar文件 按照配置大小拆分，按照词典序排列拆分在多个tar包

\* \.index文件， 记录备份文件存放在哪个tar包。还记录实例的元数据信息
以json格式组织
file_list存放备份文件与tar文件的映射信息。
```
{"backup_type":"logical","storage_engine":"InnoDB","mysql_version":"5.7.20-tmysql-3.3-log","bk_biz_id":"1111","backup_id":"243cc80c-7773-11ed-88d9-525400b22106","bill_id":"","backup_host":"127.0.0.1","backup_port":20000,"mysql_role":"master","data_schema_grant":"grant,schema","consistent_backup_time":"2022-12-09 11:39:53","file_list":[{"backup_file_name":"test-schema-create.sql.zst","backup_file_size":100,"tar_file_name":"xxxx_logical_0.tar","db_table":"test","file_type":"schema"},{"backup_file_name":"xiaogtest-schema-create.sql.zst","backup_file_size":105,"tar_file_name":"xxxx_logical_0.tar","db_table":"xiaogtest","file_type":"schema"},{"backup_file_name":"xiaogtest.t1-metadata","backup_file_size":1,"tar_file_name":"xxxx_logical_0.tar","db_table":"","file_type":"metadata"},{"backup_file_name":"xiaogtest.t1-schema.sql.zst","backup_file_size":170,"tar_file_name":"xxxx_logical_0.tar","db_table":"xiaogtest.t1","file_type":"schema"},{"backup_file_name":"xiaogtest.t1.00000.sql.zst","backup_file_size":130,"tar_file_name":"xxxx_logical_0.tar","db_table":"xiaogtest.t1","file_type":"data"}]}
```

### 物理备份
因为物理备份中一个ibd文件过大，所以我们采用先打包后拆分的方法。
即将一个tar文件拆分为多个part
```
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical.index   
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical_part_1
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical_part_2 
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical_part_3
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical_part_4 
1111_VM-165-14-centos_127.0.0.1_15000_20221227_145125_physical.priv
```
index文件内容格式为：
```
{"backup_type":"physical","storage_engine":"InnoDB","mysql_version":"8.0.18-v18-txsql-2.0.1-debug","bk_biz_id":"1111","backup_id":"e1c141f0-85b2-11ed-a7dd-525400ba6330","bill_id":"","backup_host":"127.0.0.1","backup_port":15000,"mysql_role":"master","data_schema_grant":"data, schema, grant","consistent_backup_time":"2022-12-27 14:51:25","backup_begin_time":"2022-12-27 14:51:25","backup_end_time":"2022-12-27 14:51:28","total_filesize":3262452,"binlog_info":{"show_master_status":{"binlog_file":"mysql_bin.000003","binlog_pos":"172","gtid":"c848247a-b8ac-11ed-9326-525400ba6330:1-42"},"show_slave_status":{"binlog_file":"mysql_bin.000009","binlog_pos":"212","gtid":"c848247a-b8ac-11ed-9326-525400ba6330:1-42"}},"file_list":null}
```

## 3.4 上报结果
上报三种备份信息, 文件格式为json
* 备份配置信息 (暂不上报)
文件名为：dbareport_cnf_[mysqlport].log
```
{"Public":{"BkBizId":"1111","BkCloudId":"","BillId":"","ClusterAddress":"","MysqlHost":"127.0.0.1","MysqlPort":"12000","MysqlUser":"tt","MysqlPasswd":"123456","DataSchemaGrant":"data, schema, grant","BackupDir":"/data/git-code/dbbackup/file","MysqlRole":"master","MysqlCharset":"binary","BackupTimeOut":"09:00:00","BackupType":"Logical","OldFileLeftDay":0,"TarSizeThreshold":1048576},"BackupClient":{"FileTag":"MYSQL_FULL_BACKUP","StorageType":"hdfs","DoChecksum":true},"LogicalBackup":{"PartMaxRows":1000000,"PartChunSize":1000000,"Regex":"","Threads":4,"FlushRetryCount":3,"MydumperDefaultsFile":"/data/mydumper.cnf"},"LogicalLoad":{"MysqlHost":"127.0.0.1","MysqlPort":"12001","MysqlUser":"tt","MysqlPasswd":"123456","MysqlCharset":"utf8","MysqlLoadDir":"/data/git-code/dbbackup/file/1111_VM-165-14-centos_127.0.0.1_12000_20221121_112545_Logical","Regex":"","Threads":4,"RecordBinlog":false,"MyloaderDefaultsFile":""}}
```

* 备份结果信息
文件名为： dbareport_result_[mysqlport].log
一个文件记录对应为一个json object

  其中的taskid，是由backup_client上传文件返回的Id。
  每个文件都有一个独属的taskid
```
{"backup_id":"bceb54b4-e4f3-11ed-917d-525400ba6330","bk_biz_id":"1111","bill_id":"","bk_cloud_id":"","time_zone":"CST","cluster_id":"","cluster_address":"","mysql_host":"127.0.0.1","mysql_port":12006,"master_host":"127.0.0.1","master_port":12000,"binlog_info":{"show_master_status":{"binlog_file":"mysql_bin.000003","binlog_pos":"172","gtid":""},"show_slave_status":{"binlog_file":"mysql_bin.000009","binlog_pos":"212","gtid":""}},"file_name":"1111_VM-165-14-centos_127.0.0.1_12006_20230427_200501_physical.index","backup_begin_time":"2023-04-27 20:05:01","backup_end_time":"2023-04-27 20:05:04","data_schema_grant":"data,schema,grant","backup_type":"physical","consistent_backup_time":"2023-04-27 20:05:04","mysql_role":"slave","file_size":664,"file_type":"index","task_id":"-1"}
{"backup_id":"bceb54b4-e4f3-11ed-917d-525400ba6330","bk_biz_id":"1111","bill_id":"","bk_cloud_id":"","time_zone":"CST","cluster_id":"","cluster_address":"","mysql_host":"127.0.0.1","mysql_port":12006,"master_host":"127.0.0.1","master_port":12000,"binlog_info":{"show_master_status":{"binlog_file":"mysql_bin.000003","binlog_pos":"172","gtid":""},"show_slave_status":{"binlog_file":"mysql_bin.000009","binlog_pos":"212","gtid":""}},"file_name":"1111_VM-165-14-centos_127.0.0.1_12006_20230427_200501_physical.priv","backup_begin_time":"2023-04-27 20:05:01","backup_end_time":"2023-04-27 20:05:04","data_schema_grant":"data,schema,grant","backup_type":"physical","consistent_backup_time":"2023-04-27 20:05:04","mysql_role":"slave","file_size":1448,"file_type":"priv","task_id":"-1"}
{"backup_id":"bceb54b4-e4f3-11ed-917d-525400ba6330","bk_biz_id":"1111","bill_id":"","bk_cloud_id":"","time_zone":"CST","cluster_id":"","cluster_address":"","mysql_host":"127.0.0.1","mysql_port":12006,"master_host":"127.0.0.1","master_port":12000,"binlog_info":{"show_master_status":{"binlog_file":"mysql_bin.000003","binlog_pos":"172","gtid":""},"show_slave_status":{"binlog_file":"mysql_bin.000009","binlog_pos":"212","gtid":""}},"file_name":"1111_VM-165-14-centos_127.0.0.1_12006_20230427_200501_physical.tar","backup_begin_time":"2023-04-27 20:05:01","backup_end_time":"2023-04-27 20:05:04","data_schema_grant":"data,schema,grant","backup_type":"physical","consistent_backup_time":"2023-04-27 20:05:04","mysql_role":"slave","file_size":1331712,"file_type":"tar","task_id":"-1"}
```
* 备份状态信息
文件名为：dbareport_status_[mysqlport].log
```
{"backup_id":"23d29c7a-7773-11ed-b724-525400b22106","bill_id":"","status":"Begin","report_time":"2022-12-09 11:39:52"}
{"backup_id":"23d29c7a-7773-11ed-b724-525400b22106","bill_id":"","status":"Backup","report_time":"2022-12-09 11:39:52"}
{"backup_id":"23d29c7a-7773-11ed-b724-525400b22106","bill_id":"","status":"Tar","report_time":"2022-12-09 11:39:52"}
{"backup_id":"23d29c7a-7773-11ed-b724-525400b22106","bill_id":"","status":"Report","report_time":"2022-12-09 11:39:52"}
{"backup_id":"23d29c7a-7773-11ed-b724-525400b22106","bill_id":"","status":"Success","report_time":"2022-12-09 11:39:53"}
```

## 3.4 备份加密
### 加密选项
```
[Public.EncryptOpt]
EncryptEnable = true
EncryptCmd = openssl
EncryptPublicKey =
EncryptElgo =
```
1. EncryptEnable: 是否启用备份文件加密  
   对称加密,加密密码 passphrase 随机生成
2. EncryptCmd: 加密工具，支持 `openssl`,`xbcrypt`  
  - 留空默认为 openssl
  - 如果是 xbcrypt,默认从工具目录下找 `bin/xbcrypt`，也可以指定工具全路径  
3. EncryptAlgo: 加密算法，留空会有默认加密算法
   - openssl [aes-256-cbc, aes-128-cbc, sm4-cbc]，文件后缀 `.enc`。
    sm4-cbc 为国密对称加密算法，需要 mysql 本机上的 openssl>1.1.1
   - xbcrypt [AES256, AES192, AES128]，文件后缀 `.xb`
4. EncryptPublicKey: public key 文件  
  - 用于 对 passphrase 加密，上报加密字符串。需要对应的平台 私钥 secret key 才能对 加密后的passphrase 解密
  - EncryptPublicKey 如果为空，会上报密码，仅测试用途

### EncryptPublicKey 生成示例
```
# 生成秘钥
openssl genrsa -out rsa.pem 2048
# 从秘钥文件 rsa.pem 中提取公钥
openssl rsa -pubout -in rsa.pem -out pubkey.pem
```
把 pubkey.pem 路径设置到 EncryptPublicKey

### 手动解密文件
如果没有设置 EncryptPublicKey ，可直接使用上报记录里的 key 解密，但这不安全，仅测试使用。
如果设置了 EncryptPublicKey，先要通过私钥解密出 passphrase：
```
// 1. 被加密密码 base64 解码成文件
echo -n "GiySD...bbw==" |base64 -d > encrypted.key

// 2. 使用私钥 rsa.pem 解密出 passphrase
openssl rsautl -decrypt -inkey rsa.pem -in encrypted.key

// 3. 使用密码 passphrase 解密文件
```

**用户只能拿到加密后的密码，明文 passphrase 需要从平台的页面解密获取，因为解密用的私钥不能泄露。**

- openssl 解密文件
```
openssl aes-256-cbc -d -k your_passphrase -in backupfile.tar.enc -out backupfile.tar
```
- xbcrypt 解密文件
```
xbcrypt -d -a AES256 -k your_passphrase -i backupfile.tar.xb -o backupfile.tar
```

### dbbackup filecrypt 解密文件
自动识别后缀，使用对应的解密工具
```
dbbackup filecrypt -d -k your_passphrase \
--remove-files -i backupfile.tar.xb -o backupfile.tar
// --source-dir /xxx/ --target-dir=/yyy
```

# 4. 配置文件示例

```
[Public]
BkBizId          = 123
BkCloudId        = 0
BillId           = 0
BackupId         = 
ClusterAddress   = x.x.x.x
MysqlHost        = 127.0.0.1
MysqlPort        = 3306
MysqlUser        = xx
MysqlPasswd      = xxx
DataSchemaGrant  = grant,schema
BackupDir        = /data/dbbak
MysqlRole        = master
MysqlCharset     = binary
BackupTimeout    = 09:00:00
BackupType       = physical
OldFileLeftDay   = 2
TarSizeThreshold = 8192
IOLimitMBPerSec  = 500
ResultReportPath = /home/mysql/dbareport/mysql/dbbackup/result
StatusReportPath = /home/mysql/dbareport/mysql/dbbackup/status


[BackupClient]
Enable = false
StorageType = hdfs
FileTag          = MYSQL_FULL_BACKUP
DoChecksum       = true

[LogicalBackup]
ChunkFilesize        = 2048
Regex                = ^(?!(mysql\.|test\.|sys\.|infodba_schema\.|performance_schema\.|information_schema\.))
Threads              = 4
FlushRetryCount      = 3
DisableCompress      = false
MydumperDefaultsFile = 
ExtraOpt = 

[LogicalLoad]
MysqlHost = 127.0.0.1
MysqlPort = 3307
MysqlUser = xx
MysqlPasswd = xxx
MysqlCharset = binary
MysqlLoadDir = /data/dbbak/xxx
Regex = 
Threads = 2
EnableBinlog = false
IndexFilePath = xxxx


[PhysicalBackup]
Threads = 2
SplitSpeed = 300
Throttle = 50
DefaultsFile = /etc/my.cnf.3306
ExtraOpt = 

[PhysicalLoad]
MysqlLoadDir = /data/dbbak/xxxx
Threads = 4
CopyBack = false
IndexFilePath = xx
DefaultsFile = /etc/my.cnf.3306
```

## 参数解释
### Public
- Public.KillLongQueryTime  
 这个参数对逻辑备份和物理备份作用不同，需要备份账号有 super 权限。默认为 0 则不 kill。
 - 逻辑备份 mydumper  
  相当于`--kill-long-queries --long-query-guard xx`: 发出 FTWRL 之前如果发现有超过这个时间的长 sql，则 kill 掉
 - 物理备份 xtrabackup  
   相当于`--kill-long-queries-timeout=xx`: 发出 FTWRL 之后如果被阻塞，则等待多久之后把引起阻塞的长 sql kill 掉

- Public.FtwrlWaitTimeout  
  发起备份前检查长 sql，(如果不自动 kill/ kill失败) 则等待长 sql 多久后，放弃 ftwrl，放弃备份。  
  此时还未发起 `FLUSH TABLE WITH READ LOCK` 命令。默认 120s，对 mydumper / xtrabackup 有效
  - 逻辑备份 mydumper  
    相当于 `--long-query-guard xx` 且不 kill
  - 物理备份 xtrabackup  
    5.5, 5.6 : `--lock-wait-timeout`
    5.7, 8.0 : `--ftwrl-wait-timeout`

- Public.AcquireLockWaitTimeout  
  备份加锁超时，比如 `LOCK TABLES FOR BACKUP` / `FLUSH TABLE WITH READ LOCK`，相当于 `set session lock-wait-timeout=xxx`  
  默认 10s 超时，对 mydumper / xtrabackup 有效

- Public.BackupTimeOut  
  备份超时结束时间，只对 master 有效，用于保护 master 不被备份影响。  
  默认`09:00:00`，即备份执行到这个时间点还未结束，则退出

- Public.OldFileLeftDay  
  备份文件本地最大保留时间天数，每次备份之前会先清理旧的备份。如果备份空间不足，可能会继续清理备份文件，优先保证备份成功

- Public.IOLimitMasterFactor  
  master机器专用限速因子，因为备份速度可能有多个选项来控制
  - master 文件io打包限速: `Public.IOLimitMBPerSec * IOLimitMasterFactor`
  - 物理备份限速: `PhysicalBackup.Throttle * IOLimitMasterFactor`

### LogicalBackup  
- LogicalBackup.TrxConsistencyOnly  
  mydumper `--trx-consistency-only`, 或者 mysqldump `--single-transaction`。默认 true  
  对于多引擎混合的实例，如果想要保证整体数据的全局一致，需要设置为 false，会导致在整个备份期间持有 FTWRL，在主库上谨慎使用false。

### PhysicalBackup  
- PhysicalBackup.LockDDL  
  LockDDL 备份期间是否允许 ddl, >=5.7 参数有效  
  - 默认 false，表示用户的 ddl 优先，备份无效。如果存在 Non-InnoDB 表，在拷贝这些非事务引擎表的时候，会阻塞对 Non-InnoDB dml  
  - 为 true 时，备份一开始就发送 lock tables for backup，全程不允许 ddl 和 Non-InnoDB dml  
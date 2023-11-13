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
[public]
  BkBizId          string `ini:"BkBizId"`
  BkCloudId       string `ini:"BkCloudId"`
  BillId          string `ini:"BillId"`
  ClusterAddress  string `ini:"ClusterAddress"`
  MysqlHost       string `ini:"MysqlHost"`
  MysqlPort       string `ini:"MysqlPort"`
  MysqlUser       string `ini:"MysqlUser"`
  MysqlPasswd     string `ini:"MysqlPasswd"`
  DataSchemaGrant string `ini:"DataSchemaGrant"` [data,schema,grant] data表示表内数据，schema表示表结构，grant代表权限信息。例如输入 data 表示只备份表内信息，输入 data, grant表示备份表内数据和权限信息， 输入data, schema, grant表示上述三种信息数据都备份。输入你想备份的信息名称，并用`,`连接起来，输入的信息名称必须是data,schema,grant中的一种，否则视为非法输入。也可单独输入all，相当于data,schema,grant。
  BackupDir       string `ini:"BackupDir"`
  MysqlRole       string `ini:"MysqlRole"`  [master|slave]
  MysqlCharset    string `ini:"MysqlCharset"`
  BackupTimeOut   string `ini:"BackupTimeout"` //example: 09:00:00
  BackupType      string `ini:"BackupType"`  [logical|physical]
  OldFileLeftDay         int    `ini:"OldFileLeftDay"`
  TarSizeThreshold uint64 `ini:"TarSizeThreshold"`
[BackupClient]
  FileTag          string `ini:"FileTag"`
  RemoteFileSystem string `ini:"RemoteFileSystem"`  [hdfs|cos]
  DoChecksum       bool   `ini:"DoChecksum"`    //默认为true
[LogicalBackup]
  PartMaxRows          uint64 `ini:"PartMaxRows"`
  PartChunkSize         uint64 `ini:"PartChunkSize"`
  Regex                 string `ini:"Regex"`
  Threads               int    `ini:"Threads"`
  FlushRetryCount       int    `ini:"FlushRetryCount"`
  MydumperDefaultsFile string `ini:"MydumperDefaultsFile"`  //暂未启用
[PhysicalBackup]
  Threads           int    `ini:"Threads"`
  SplitSpeed        int64  `ini:"SplitSpeed"` // MB/s
  MysqlDefaultsFile string `ini:"MysqlDefaultsFile"`
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
{"Public":{"BkBizId":"1111","BkCloudId":"","BillId":"","ClusterAddress":"","MysqlHost":"127.0.0.1","MysqlPort":"12000","MysqlUser":"tt","MysqlPasswd":"123456","DataSchemaGrant":"data, schema, grant","BackupDir":"/data/git-code/dbbackup/file","MysqlRole":"master","MysqlCharset":"binary","BackupTimeOut":"09:00:00","BackupType":"Logical","OldFileLeftDay":0,"TarSizeThreshold":1048576},"BackupClient":{"FileTag":"MYSQL_FULL_BACKUP","RemoteFileSystem":"hdfs","DoChecksum":true},"LogicalBackup":{"PartMaxRows":1000000,"PartChunSize":1000000,"Regex":"","Threads":4,"FlushRetryCount":3,"MydumperDefaultsFile":"/data/mydumper.cnf"},"LogicalLoad":{"MysqlHost":"127.0.0.1","MysqlPort":"12001","MysqlUser":"tt","MysqlPasswd":"123456","MysqlCharset":"utf8","MysqlLoadDir":"/data/git-code/dbbackup/file/1111_VM-165-14-centos_127.0.0.1_12000_20221121_112545_Logical","Regex":"","Threads":4,"RecordBinlog":false,"MyloaderDefaultsFile":""}}
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
   - openssl [aes-256-cbc, aes-128-cbc, sm4-cbc]，文件后缀 `.enc`。sm4-cbc 为国密对称加密算法
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
一般 passphrase 需要从平台的页面获取，因为私钥不能泄露给使用者。

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
RemoteFileSystem = hdfs
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
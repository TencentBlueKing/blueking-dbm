### 1. 怎么改备份类型：物理备份、逻辑备份
**如果是永久修改，则修改配置文件** 
```
[Public]
BackupType      =       logical
```
BackupType 可选值：`logical`, `physical`, `auto`
`auto` 表示自动选择备份类型，自动判断条件：
 - 当机器 glibc 版本 < 2.14 (centos 6.x)，`physical`
 - 当数据目录的数据量 > 400G 时，`physical`
 - 当机器 glibc 版本 >=2.14 且数据量小于 400G，`logical`

**如果是临时发起一次逻辑备份**
可不用修改配置文件
```
./dbbackup dumpbackup -c dbbackup.3306.ini --backup-type logical
```

### 2. 怎么修改备份内容：表结构、数据
```
[Public]
DataSchemaGrant = all
```
可选值有 `all`, `schema`, `data`, `grant`， 也可以组合使用 `schema,grant`, `all` 相当于别称`schema,data,grant`

### 3. 备份空间不足，但人为评估磁盘应该能放得下
如果评估压缩率比较高，或者空洞率比较高，逻辑备份空间够用，可发起一次备份加上选项 `--nocheck-diskspace`
```
./dbbackup dumpbackup -c dbbackup.3306.ini --backup-type logical  --nocheck-diskspace
```
每次备份之后，都会往 `infodba_schema.local_backup_report` 里记录一条备份信息，下一次备份时遇到空间不足，会从这里读取上次备份的文件大小来判断空间。
不建议将 `Public.NoCheckDiskSpace` 持久化到配置文件

### 4. 怎么修改备份开始时间
进入 mysql-crond 任务调度程序目录
```
cd /home/mysql/mysql-crond
vim jobs-config.yaml

    - name: dbbackup-schedule
      enable: true
      command: /home/mysql/dbbackup-go/dbbackup_main.sh
      args:
        - '>'
        - /home/mysql/dbbackup-go/logs/main.log
        - 2>&1
      schedule: 3 3 * * *
      creator: system
      work_dir: /home/mysql/dbbackup-go
      
修改 schedule
```

### 5. 怎么调整磁盘 io 限速
限速分为 2 个阶段：导出阶段，打包切分阶段

导出阶段:
```
logical 暂时不支持导出限速

physical 可设置 PhysicalBackup.Throttle, 单位是每秒拷贝 chunk 数量，一个 chunk 10MB。但总速度得结合 Threads 来设置
[PhysicalBackup]
Throttle = 200
Threads = 2
```

打包切分阶段：
```
物理备份、逻辑备份的打包切分，都受到 Public.IOLimitMBPerSec 控制，单位 MB/s
[Public]
IOLimitMBPerSec = 300
```
参数 `Public.IOLimitMasterFactor = 0.5` 可进一步限制在 master 上备份的限速，表示的是限速因子，比如 0.5 表示实际限速为 `IOLimitMBPerSec * 0.5`, `Throttle * 0.5`

### 6. 关于 tendbcluster 集群备份，请参考 [spider](spiderbackup.md)

### 常见备份失败处理

1. log copying being too slow
it looks like InnoDB log has wrapped around before xtrabackup could process all records due to either log copying being too slow, or  log files being too small.
 实例写入速度比备份速度快，可能是刚刚备份时间段有大批量 DML 操作，修改备份开始时间，或者加快备份速度: 
  - 调大 PhysicalBackup.Throttle, 调大 PhysicalBackup.Threads